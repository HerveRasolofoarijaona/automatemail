import os
import logging
from datetime import datetime
import oracledb

logger = logging.getLogger('send_report')

# Variable globale pour tracker l'initialisation
_oracle_initialized = False


def _init_oracle_thick():
    """
    Initialise Oracle en mode THICK si ORACLE_CLIENT_LIB est défini.
    Appelé automatiquement au chargement du module.
    """
    global _oracle_initialized
    if _oracle_initialized:
        return
    
    client_lib = os.getenv("ORACLE_CLIENT_LIB")
    if client_lib:
        try:
            oracledb.init_oracle_client(lib_dir=client_lib)
            logger.info("Oracle client initialisé (THICK mode) depuis : %s", client_lib)
            _oracle_initialized = True
        except oracledb.ProgrammingError as e:
            # Déjà initialisé
            logger.debug("Oracle client déjà initialisé : %s", e)
            _oracle_initialized = True
        except Exception as e:
            logger.error("Erreur initialisation Oracle client : %s", e)
            raise
    else:
        logger.warning("ORACLE_CLIENT_LIB non défini, impossible d'utiliser le mode THICK")


# ✅ Appel immédiat au chargement du module
_init_oracle_thick()


def get_oracle_connection():
    """
    Établit une connexion à Oracle.
    
    Le mode (THIN/THICK) est déterminé par la présence de ORACLE_CLIENT_LIB.
    
    Nécessite les variables d'environnement:
    - ORACLE_HOST
    - ORACLE_PORT
    - ORACLE_SERVICE
    - ORACLE_USER
    - ORACLE_PASSWORD
    - ORACLE_CLIENT_LIB (optionnel, pour mode THICK)
    """
    host = os.getenv("ORACLE_HOST")
    port = os.getenv("ORACLE_PORT")
    service = os.getenv("ORACLE_SERVICE")
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_PASSWORD")
    
    # Validation des variables
    if not all([host, port, service, user, password]):
        missing = [k for k, v in {
            "ORACLE_HOST": host,
            "ORACLE_PORT": port,
            "ORACLE_SERVICE": service,
            "ORACLE_USER": user,
            "ORACLE_PASSWORD": password
        }.items() if not v]
        raise ValueError(f"Variables d'environnement manquantes: {', '.join(missing)}")
    
    # Format DSN: host:port/service
    dsn = f"{host}:{port}/{service}"
    
    logger.debug(f"Connexion Oracle: {user}@{dsn}")
    
    try:
        connection = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn
        )
        logger.info(f"Connexion réussie - Version Oracle: {connection.version}")
        return connection
    except oracledb.DatabaseError as e:
        logger.error(f"Erreur de connexion Oracle: {e}")
        raise


def fetch_reports(
    report_type: str,
    nd: str,
    date_debut: datetime,
    date_fin: datetime,
    partition: str | None = None,
) -> list[dict]:
    """
    Récupère les rapports depuis Oracle selon les critères.
    
    Args:
        report_type: Type de rapport ('remit', 'up', 'down', etc.)
        nd: Numéro de téléphone
        date_debut: Date de début
        date_fin: Date de fin
        partition: Nom de la partition Oracle (optionnel)
    
    Returns:
        Liste de dictionnaires contenant les résultats
    """
    logger.debug("=== Paramètres fetch_reports ===")
    logger.debug(f"report_type  : {report_type}")
    logger.debug(f"nd           : {nd}")
    logger.debug(f"date_debut   : {date_debut}")
    logger.debug(f"date_fin     : {date_fin}")
    logger.debug(f"partition    : {partition}")
    
    conn = None
    cursor = None
    
    try:
        logger.debug("Requête Oracle en cours")
        conn = get_oracle_connection()
        cursor = conn.cursor()
        
        # Construction de la requête selon le type de rapport
        if report_type.lower() == "remit":
            query = """
        SELECT
            tr.MODIFIED AS DATE_TRANS,
            tr.TRANSID AS REFMVOLA,
            tr.TRANS_TYPE,
            tr.INITIATOR,
            tr.AMOUNT,
            tr.DEBTOR,
            tr.CREDITOR,
            tr.STATE,
            tr.C_PRE_BAL AS BALANCE_AVANT,
            tr.C_POST_BAL AS BALANCE_APRES,
            
            MAX(CASE WHEN td.TD_KEY = 'operationType' THEN td.VALUE END) AS OPERATION_TYPE,
            MAX(CASE WHEN td.TD_KEY = 'descriptionText' THEN td.VALUE END) AS DESCRIPTION,
            MAX(CASE WHEN td.TD_KEY = 'partnerID' THEN td.VALUE END) AS PARTNER_ID,
            MAX(CASE WHEN td.TD_KEY = 'partnerWalletId' THEN td.VALUE END) AS PARTNER_WALLET_ID,
            MAX(CASE WHEN td.TD_KEY = 'partnerWorkflowID' THEN td.VALUE END) AS PARTNER_WORKFLOW_ID,
            MAX(CASE WHEN td.TD_KEY = 'sendingPartnerName' THEN td.VALUE END) AS SENDING_PARTNER,
            MAX(CASE WHEN td.TD_KEY = 'receiverFirstname' THEN td.VALUE END) AS RECEIVER_FIRSTNAME,
            MAX(CASE WHEN td.TD_KEY = 'receiverName' THEN td.VALUE END) AS RECEIVER_NAME,
            MAX(CASE WHEN td.TD_KEY = 'receiverAmount' THEN td.VALUE END) AS RECEIVER_AMOUNT,
            MAX(CASE WHEN td.TD_KEY = 'receiverCurrency' THEN td.VALUE END) AS RECEIVER_CURRENCY,
            MAX(CASE WHEN td.TD_KEY = 'senderFirstname' THEN td.VALUE END) AS SENDER_FIRSTNAME,
            MAX(CASE WHEN td.TD_KEY = 'senderName' THEN td.VALUE END) AS SENDER_NAME,
            MAX(CASE WHEN td.TD_KEY = 'senderAccountID' THEN td.VALUE END) AS SENDER_ACCOUNT_ID,
            MAX(CASE WHEN td.TD_KEY = 'senderAmount' THEN td.VALUE END) AS SENDER_AMOUNT,
            MAX(CASE WHEN td.TD_KEY = 'senderCurrency' THEN td.VALUE END) AS SENDER_CURRENCY,
            MAX(CASE WHEN td.TD_KEY = 'senderCountry' THEN td.VALUE END) AS SENDER_COUNTRY,
            MAX(CASE WHEN td.TD_KEY = 'trans_ext_reference' THEN td.VALUE END) AS EXT_REFERENCE
            
        FROM MCOMMADM.TRANS_REPORT{partition_clause} tr
        LEFT JOIN MCOMMADM.TRANS_DATA td ON td.TRANSID = tr.TRANSID
        WHERE 
            (tr.INITIATOR = :nd OR tr.CREDITOR = :nd OR tr.DEBTOR = :nd)
            AND tr.TRANS_TYPE NOT IN (
                'login','balance','logout','create_batch','report','trans_query_ext'
            )
            AND tr.MODIFIED BETWEEN :date_debut AND :date_fin
        GROUP BY 
            tr.MODIFIED,
            tr.TRANSID,
            tr.TRANS_TYPE,
            tr.INITIATOR,
            tr.AMOUNT,
            tr.DEBTOR,
            tr.CREDITOR,
            tr.STATE,
            tr.C_PRE_BAL,
            tr.C_POST_BAL
        ORDER BY tr.MODIFIED ASC
            """
            
            # Ajouter la partition si spécifiée
            partition_clause = f" PARTITION ({partition})" if partition else ""
            query = query.replace("{partition_clause}", partition_clause)
            
            params = {
                'nd': nd,
                'date_debut': date_debut,
                'date_fin': date_fin
            }
            
        elif report_type.lower() == "up":
            query = """
                    SELECT
                    tr.MODIFIED AS DATE_TRANS,
                    tr.TRANSID AS N_TRANSACTION,
                    tr.INITIATOR,
                    tr.TRANS_TYPE,
                    tr.CHANNEL,
                    tr.STATE,
                    CASE WHEN tr.WALLET = 'EWallet' THEN 'M_Vola' ELSE tr.WALLET END AS COMPTE,
                    tr.AMOUNT,
                    tr.RRP,
                    tr.DEBTOR,
                    tr.CREDITOR,
                    tr.D_PRE_BAL AS DE_BALANCE_AVANT,
                    tr.D_POST_BAL AS DE_BALANCE_APRES,
                    tr.C_PRE_BAL AS VERS_BALANCE_AVANT,
                    tr.C_POST_BAL AS VERS_BALANCE_APRES,
                    tr.DETAILS1,
                    tr.DETAILS2
                FROM MCOMMADM.TRANS_REPORT {partition_clause} tr
                WHERE
                    (tr.INITIATOR = :nd OR tr.DEBTOR = :nd OR tr.CREDITOR = :nd)
                    AND tr.TRANS_TYPE NOT IN (
                        'login','balance','logout','create_batch','report','trans_query_ext'
                    )
                    AND tr.MODIFIED BETWEEN :date_debut AND :date_fin
                ORDER BY tr.MODIFIED DESC
            """
            
            partition_clause = f" PARTITION ({partition})" if partition else ""
            query = query.replace("{partition_clause}", partition_clause)
            
            params = {
                'nd': nd,
                'date_debut': date_debut,
                'date_fin': date_fin
            }
            
        
        else:
            raise ValueError(f"Type de rapport non supporté: {report_type}")
        
        logger.debug("=== Requête SQL exécutée ===")
        logger.debug(query)
        
        cursor.execute(query, params)
        
        # Récupérer les noms des colonnes
        columns = [col[0] for col in cursor.description]
        
        # Convertir les résultats en liste de dictionnaires
        results = []
        for row in cursor:
            results.append(dict(zip(columns, row)))
        
        logger.info(f"Requête réussie: {len(results)} lignes récupérées")
        
        return results
        
    except oracledb.DatabaseError as e:
        logger.error(f"Erreur requête Oracle: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logger.debug("Connexion Oracle fermée")