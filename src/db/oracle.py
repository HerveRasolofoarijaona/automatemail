import os
import oracledb
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


def get_oracle_connection():
    dsn = oracledb.makedsn(
        host=os.getenv("ORACLE_HOST"),
        port=os.getenv("ORACLE_PORT"),
        service_name=os.getenv("ORACLE_SERVICE"),
    )

    return oracledb.connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=dsn,
    )


def fetch_reports(
    report_type: str,
    nd: str,
    date_debut: datetime,
    date_fin: datetime,
    partition: str | None = None,
):
    if report_type == "remit":
        if not partition:
            raise ValueError("partition obligatoire pour report_type=remit")

        sql = f"""
        SELECT
            tr.MODIFIED,
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

        FROM MCOMMADM.TRANS_REPORT PARTITION ({partition}) tr
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

    elif report_type == "up":
        if not partition:
            raise ValueError("partition obligatoire pour report_type=up")

        sql = f"""
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
        FROM MCOMMADM.TRANS_REPORT PARTITION ({partition}) tr
        WHERE
            (tr.INITIATOR = :nd OR tr.DEBTOR = :nd OR tr.CREDITOR = :nd)
            AND tr.TRANS_TYPE NOT IN (
                'login','balance','logout','create_batch','report','trans_query_ext'
            )
            AND tr.MODIFIED BETWEEN :date_debut AND :date_fin
        ORDER BY tr.MODIFIED DESC
        """

    else:
        raise ValueError(f"report_type inconnu : {report_type}")

    with get_oracle_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                sql,
                nd=nd,
                date_debut=date_debut,
                date_fin=date_fin,
            )

            columns = [c[0] for c in cursor.description]
            rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]