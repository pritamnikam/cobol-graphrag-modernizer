"""Seed a repeatable, interconnected COBOL/JCL modernization sample workspace."""

import os


# A declarative asset manifest keeps the generated sample graph understandable:
# shared job names, CALL targets, and COPY members deliberately cross domains.
WORKSPACE_ASSETS = {
    # Common batch prerequisites are referenced by multiple capability jobs.
    "jcl/WEEKLY_BILLING.jcl": """
        //WEEKLY01 JOB (ACCT100),'WEEKLY BILLING RUN',CLASS=A,MSGCLASS=X
        //* DEPENDS-ON: COMMON_PRECHECK
        //STEP10 EXEC PGM=CUSTUPD0
        //STEPLIB DD DSN=PROD.LOADLIB,DISP=SHR
        //CUSTFILE DD DSN=PROD.CUSTOMER.MASTER,DISP=SHR
        //RPTFILE DD DSN=PROD.BILLING.REPORT,DISP=(NEW,CATLG)
        """,
    "jcl/MONTH_END.jcl": """
        //MONTHEND JOB (ACCT100),'MONTHLY INTEREST RUN',CLASS=A,MSGCLASS=X
        //* DEPENDS-ON: WEEKLY_BILLING
        //STEP20 EXEC PGM=INTRCALC
        //STEPLIB DD DSN=PROD.LOADLIB,DISP=SHR
        //CUSTFILE DD DSN=PROD.CUSTOMER.MASTER,DISP=SHR
        //INTFILE DD DSN=PROD.INTEREST.LOG,DISP=(NEW,CATLG)
        """,
    "jcl/COMMON_PRECHECK.jcl": """
        //PRECHECK JOB (SYS100),'SHARED BATCH PRECHECK',CLASS=A,MSGCLASS=X
        //DATECHK EXEC PGM=DATEUTIL
        //AMTCHK EXEC PGM=AMOUNTUT
        """,
    "jcl/COMMON_RECONCILIATION.jcl": """
        //COMMONRC JOB (SYS100),'SHARED RECONCILIATION',CLASS=A,MSGCLASS=X
        //* DEPENDS-ON: COMMON_PRECHECK
        //AUDIT EXEC PGM=AUDITLOG
        //DATECHK EXEC PGM=DATEUTIL
        """,
    "jcl/PAYMENT_CYCLE.jcl": """
        //PAYCYCLE JOB (PAY200),'PAYMENT CYCLE',CLASS=A,MSGCLASS=X
        //* DEPENDS-ON: COMMON_PRECHECK
        //AUTH EXEC PGM=PAYAUTH
        //PAYFILE DD DSN=PROD.PAYMENT.INPUT,DISP=SHR
        //POST EXEC PGM=PAYPOST
        //LEDGER DD DSN=PROD.PAYMENT.LEDGER,DISP=SHR
        """,
    "jcl/LOAN_SERVICING.jcl": """
        //LOANSERV JOB (LN300),'DAILY LOAN SERVICING',CLASS=A,MSGCLASS=X
        //* DEPENDS-ON: COMMON_PRECHECK
        //PAYMENT EXEC PGM=LOANPMT
        //LOANFILE DD DSN=PROD.LOAN.MASTER,DISP=SHR
        //ACCRUAL EXEC PGM=LOANINT
        //INTFILE DD DSN=PROD.LOAN.INTEREST,DISP=SHR
        """,
    "jcl/CARD_SETTLEMENT.jcl": """
        //CARDSET JOB (CARD400),'CARD SETTLEMENT',CLASS=A,MSGCLASS=X
        //* DEPENDS-ON: PAYMENT_CYCLE
        //AUTH EXEC PGM=CARDAUTH
        //CARDFILE DD DSN=PROD.CARD.MASTER,DISP=SHR
        //SETTLE EXEC PGM=CARDSETL
        //SETLFILE DD DSN=PROD.CARD.SETTLEMENT,DISP=SHR
        """,
    "jcl/CLAIMS_PROCESSING.jcl": """
        //CLAIMS JOB (CLM500),'CLAIMS DAILY PROCESS',CLASS=A,MSGCLASS=X
        //* DEPENDS-ON: COMMON_PRECHECK
        //INTAKE EXEC PGM=CLAIMIN
        //CLMFILE DD DSN=PROD.CLAIMS.INPUT,DISP=SHR
        //ADJUST EXEC PGM=CLAIMADJ
        //RESFILE DD DSN=PROD.CLAIMS.RESERVE,DISP=SHR
        """,
    "jcl/REGULATORY_REPORTING.jcl": """
        //REGREPORT JOB (RPT600),'REGULATORY REPORTING',CLASS=A,MSGCLASS=X
        //* DEPENDS-ON: PAYMENT_CYCLE
        //* DEPENDS-ON: CARD_SETTLEMENT
        //* DEPENDS-ON: COMMON_RECONCILIATION
        //SCREEN EXEC PGM=AMLSCAN
        //TXNFILE DD DSN=PROD.TRANSACTION.DAILY,DISP=SHR
        //RECON EXEC PGM=REGRECON
        //RPTFILE DD DSN=PROD.REGULATORY.REPORT,DISP=(NEW,CATLG)
        """,
    "jcl/CUSTOMER_ONBOARDING.jcl": """
        //CUSTONBD JOB (CUST700),'CUSTOMER ONBOARDING',CLASS=A,MSGCLASS=X
        //* DEPENDS-ON: COMMON_PRECHECK
        //CREATE EXEC PGM=CUSTONBD
        //CUSTFILE DD DSN=PROD.CUSTOMER.NEW,DISP=SHR
        //VERIFY EXEC PGM=KYCVERIFY
        //KYCFILE DD DSN=PROD.CUSTOMER.KYC,DISP=SHR
        """,
    "jcl/TREASURY_CASH.jcl": """
        //TREASURY JOB (TRS800),'TREASURY CASH POSITION',CLASS=A,MSGCLASS=X
        //* DEPENDS-ON: COMMON_PRECHECK
        //* DEPENDS-ON: PAYMENT_CYCLE
        //POST EXEC PGM=CASHPOST
        //CASHFILE DD DSN=PROD.TREASURY.CASH,DISP=SHR
        //FORECAST EXEC PGM=CASHFCST
        //FCSTFILE DD DSN=PROD.TREASURY.FORECAST,DISP=(NEW,CATLG)
        """,
    # Programs model domain behavior and call shared utility modules to make
    # cross-capability dependencies visible during parsing and graph traversal.
    "programs/CUSTUPD0.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTUPD0.
       * REMARKS. Updates customer service tiers from account balances for
       *          weekly billing and customer account management.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-EOF-SW PIC X VALUE 'N'.
       COPY CUSTREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       MAIN-LOGIC.
           CALL 'DATEUTIL'
           CALL 'AUDITLOG'
           IF CUST-BALANCE > 10000.00
               MOVE 'VIP' TO CUST-TIER
           ELSE
               MOVE 'REG' TO CUST-TIER
           END-IF
           STOP RUN.
       """,
    "programs/INTRCALC.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. INTRCALC.
       * REMARKS. Calculates monthly compound interest for eligible
       *          customer accounts and updates the accrued ledger amount.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-INTEREST-RATE PIC V999 VALUE 0.045.
       01 WS-CALC-AMOUNT PIC 9(07)V99 VALUE 0.
       COPY CUSTREC.
       COPY ACCTREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       CALCULATE-INTEREST.
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           IF CUST-TIER = 'VIP'
               COMPUTE WS-CALC-AMOUNT =
                   CUST-BALANCE * WS-INTEREST-RATE
               ADD WS-CALC-AMOUNT TO ACCT-ACCRUED
           END-IF
           STOP RUN.
       """,
    "programs/PAYAUTH.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYAUTH.
       * REMARKS. Validates payment amount and account status before
       *          authorizing customer payments and transfers.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY PAYREC.
       COPY CUSTREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       AUTHORIZE-PAYMENT.
           CALL 'DATEUTIL'
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           IF PAY-AMOUNT > 0 AND PAY-STATUS = 'NEW'
               MOVE 'AUTH' TO PAY-STATUS
           ELSE
               MOVE 'REJT' TO PAY-STATUS
           END-IF
           STOP RUN.
       """,
    "programs/PAYPOST.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYPOST.
       * REMARKS. Posts authorized payments to the settlement ledger and
       *          records the final payment status.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY PAYREC.
       COPY LEDGERREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       POST-PAYMENT.
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           IF PAY-STATUS = 'AUTH'
               ADD PAY-AMOUNT TO LEDGER-BALANCE
               MOVE 'POST' TO PAY-STATUS
           END-IF
           STOP RUN.
       """,
    "programs/LOANPMT.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. LOANPMT.
       * REMARKS. Applies scheduled borrower payments to outstanding
       *          principal and tracks delinquent loan accounts.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY LOANREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       APPLY-LOAN-PAYMENT.
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           IF LOAN-PAYMENT > 0
               SUBTRACT LOAN-PAYMENT FROM LOAN-PRINCIPAL
               MOVE 'CURRENT' TO LOAN-STATUS
           ELSE
               MOVE 'PAST-DUE' TO LOAN-STATUS
           END-IF
           STOP RUN.
       """,
    "programs/LOANINT.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. LOANINT.
       * REMARKS. Accrues daily interest on active loans using the
       *          contractual rate and outstanding principal.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-DAILY-INTEREST PIC 9(07)V99 VALUE 0.
       COPY LOANREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       ACCRUE-LOAN-INTEREST.
           CALL 'DATEUTIL'
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           IF LOAN-STATUS = 'CURRENT'
               COMPUTE WS-DAILY-INTEREST =
                   LOAN-PRINCIPAL * LOAN-RATE / 365
               ADD WS-DAILY-INTEREST TO LOAN-ACCRUED
           END-IF
           STOP RUN.
       """,
    "programs/CARDAUTH.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CARDAUTH.
       * REMARKS. Authorizes card transactions by checking card status,
       *          transaction amount, and available credit.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CARDREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       AUTHORIZE-CARD.
           CALL 'DATEUTIL'
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           IF CARD-STATUS = 'OPEN'
               AND CARD-AMOUNT <= CARD-AVAILABLE
               MOVE 'AUTH' TO CARD-DECISION
           ELSE
               MOVE 'DECL' TO CARD-DECISION
           END-IF
           STOP RUN.
       """,
    "programs/CARDSETL.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CARDSETL.
       * REMARKS. Settles authorized card transactions and reduces the
       *          cardholder's available credit.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CARDREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       SETTLE-CARD-TRANSACTION.
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           IF CARD-DECISION = 'AUTH'
               SUBTRACT CARD-AMOUNT FROM CARD-AVAILABLE
               MOVE 'SETL' TO CARD-DECISION
           END-IF
           STOP RUN.
       """,
    "programs/CLAIMIN.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CLAIMIN.
       * REMARKS. Validates incoming policy claims and assigns them to
       *          the appropriate claims-processing status.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CLAIMREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       VALIDATE-CLAIM.
           CALL 'DATEUTIL'
           CALL 'AUDITLOG'
           IF CLAIM-AMOUNT > 0 AND CLAIM-POLICY-STATUS = 'ACTIVE'
               MOVE 'READY' TO CLAIM-STATUS
           ELSE
               MOVE 'PEND' TO CLAIM-STATUS
           END-IF
           STOP RUN.
       """,
    "programs/CLAIMADJ.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CLAIMADJ.
       * REMARKS. Calculates claim reserves for validated claims and
       *          records approved adjustment amounts.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-RESERVE PIC 9(07)V99 VALUE 0.
       COPY CLAIMREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       ADJUST-CLAIM-RESERVE.
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           IF CLAIM-STATUS = 'READY'
               COMPUTE WS-RESERVE = CLAIM-AMOUNT * 0.80
               MOVE WS-RESERVE TO CLAIM-RESERVE
           END-IF
           STOP RUN.
       """,
    "programs/AMLSCAN.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. AMLSCAN.
       * REMARKS. Flags high-value transactions for anti-money-laundering
       *          review and regulatory compliance screening.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY TXNREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       SCREEN-TRANSACTION.
           CALL 'DATEUTIL'
           CALL 'AUDITLOG'
           IF TXN-AMOUNT >= 10000.00
               MOVE 'REVIEW' TO TXN-REVIEW-STATUS
           ELSE
               MOVE 'CLEAR' TO TXN-REVIEW-STATUS
           END-IF
           STOP RUN.
       """,
    "programs/REGRECON.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. REGRECON.
       * REMARKS. Reconciles daily transaction totals and prepares
       *          controlled data for regulatory reporting.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY TXNREC.
       COPY REPORTREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       RECONCILE-REPORT.
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           ADD TXN-AMOUNT TO REPORT-TOTAL
           ADD 1 TO REPORT-RECORD-COUNT
           STOP RUN.
       """,
    "programs/CUSTONBD.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTONBD.
       * REMARKS. Creates a new customer profile and initializes its
       *          customer and audit records for onboarding.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTREC.
       COPY KYC-AUDIT-REC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       CREATE-CUSTOMER.
           CALL 'DATEUTIL'
           CALL 'AUDITLOG'
           MOVE 'PEND' TO KYC-STATUS
           STOP RUN.
       """,
    "programs/KYCVERIFY.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. KYCVERIFY.
       * REMARKS. Verifies customer identity and compliance documents
       *          before activating a newly onboarded account.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTREC.
       COPY KYC-AUDIT-REC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       VERIFY-CUSTOMER.
           CALL 'DATEUTIL'
           CALL 'AUDITLOG'
           IF KYC-DOCUMENT-STATUS = 'VALID'
               MOVE 'ACTIVE' TO KYC-STATUS
           ELSE
               MOVE 'REVIEW' TO KYC-STATUS
           END-IF
           STOP RUN.
       """,
    "programs/CASHPOST.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CASHPOST.
       * REMARKS. Consolidates posted payment and settlement activity
       *          into the daily treasury cash position.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CASHREC.
       COPY LEDGERREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       POST-CASH-POSITION.
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           ADD LEDGER-BALANCE TO CASH-AVAILABLE
           STOP RUN.
       """,
    "programs/CASHFCST.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CASHFCST.
       * REMARKS. Produces a short-term cash forecast from current
       *          treasury balances and scheduled payment obligations.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-NET-FLOW PIC 9(11)V99 VALUE 0.
       COPY CASHREC.
       COPY LEDGERREC.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       FORECAST-CASH.
           CALL 'DATEUTIL'
           CALL 'AMOUNTUT'
           CALL 'AUDITLOG'
           COMPUTE WS-NET-FLOW =
               CASH-AVAILABLE - CASH-SCHEDULED-PAYMENTS
           MOVE WS-NET-FLOW TO CASH-FORECAST
           STOP RUN.
       """,
    # Shared copybooks make record-layout reuse explicit across programs.
    "copybooks/CUSTREC.cpy": """
       01 CUSTOMER-RECORD.
          05 CUST-ID PIC X(08).
          05 CUST-NAME PIC X(30).
          05 CUST-BALANCE PIC 9(07)V99.
          05 CUST-TIER PIC X(03).
       """,
    "copybooks/ACCTREC.cpy": """
       01 ACCOUNT-LEDGER-RECORD.
          05 ACCT-ID PIC X(10).
          05 ACCT-LEDGER PIC X(04).
          05 ACCT-ACCRUED PIC 9(05)V99.
       """,
    "copybooks/PAYREC.cpy": """
       01 PAYMENT-RECORD.
          05 PAY-ID PIC X(12).
          05 PAY-ACCOUNT-ID PIC X(10).
          05 PAY-AMOUNT PIC 9(09)V99.
          05 PAY-STATUS PIC X(04).
       """,
    "copybooks/LEDGERREC.cpy": """
       01 PAYMENT-LEDGER-RECORD.
          05 LEDGER-ACCOUNT-ID PIC X(10).
          05 LEDGER-BALANCE PIC 9(11)V99.
       """,
    "copybooks/LOANREC.cpy": """
       01 LOAN-RECORD.
          05 LOAN-ID PIC X(10).
          05 LOAN-PRINCIPAL PIC 9(09)V99.
          05 LOAN-PAYMENT PIC 9(07)V99.
          05 LOAN-RATE PIC V9999.
          05 LOAN-ACCRUED PIC 9(07)V99.
          05 LOAN-STATUS PIC X(08).
       """,
    "copybooks/CARDREC.cpy": """
       01 CARD-TRANSACTION-RECORD.
          05 CARD-ID PIC X(16).
          05 CARD-STATUS PIC X(06).
          05 CARD-AMOUNT PIC 9(07)V99.
          05 CARD-AVAILABLE PIC 9(09)V99.
          05 CARD-DECISION PIC X(04).
       """,
    "copybooks/CLAIMREC.cpy": """
       01 CLAIM-RECORD.
          05 CLAIM-ID PIC X(12).
          05 CLAIM-POLICY-STATUS PIC X(08).
          05 CLAIM-AMOUNT PIC 9(09)V99.
          05 CLAIM-RESERVE PIC 9(09)V99.
          05 CLAIM-STATUS PIC X(08).
       """,
    "copybooks/TXNREC.cpy": """
       01 TRANSACTION-RECORD.
          05 TXN-ID PIC X(12).
          05 TXN-ACCOUNT-ID PIC X(10).
          05 TXN-AMOUNT PIC 9(09)V99.
          05 TXN-REVIEW-STATUS PIC X(08).
       """,
    "copybooks/REPORTREC.cpy": """
       01 REGULATORY-REPORT-RECORD.
          05 REPORT-TOTAL PIC 9(13)V99.
          05 REPORT-RECORD-COUNT PIC 9(09).
       """,
    "copybooks/AUDITREC.cpy": """
       01 AUDIT-RECORD.
          05 AUDIT-EVENT-ID PIC X(16).
          05 AUDIT-EVENT-TYPE PIC X(12).
          05 AUDIT-TIMESTAMP PIC X(26).
       """,
    "copybooks/KYC-AUDIT-REC.cpy": """
       01 KYC-RECORD.
          05 KYC-CUSTOMER-ID PIC X(08).
          05 KYC-DOCUMENT-STATUS PIC X(08).
          05 KYC-STATUS PIC X(08).
       """,
    "copybooks/CASHREC.cpy": """
       01 TREASURY-CASH-RECORD.
          05 CASH-AVAILABLE PIC 9(11)V99.
          05 CASH-SCHEDULED-PAYMENTS PIC 9(11)V99.
          05 CASH-FORECAST PIC 9(11)V99.
       """,
    # Utility programs are stored as COBOL so the existing parser indexes them
    # as Program nodes and can resolve static CALL relationships to them.
    "utils/DATEUTIL.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. DATEUTIL.
       * REMARKS. Shared date validation utility used by batch processing.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-DATE-VALID PIC X VALUE 'N'.
       PROCEDURE DIVISION.
       VALIDATE-DATE.
           DISPLAY 'DATE VALIDATION UTILITY'
           GOBACK.
       """,
    "utils/AMOUNTUT.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. AMOUNTUT.
       * REMARKS. Shared financial amount normalization utility for
       *          payments, loans, cards, and claims.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-AMOUNT PIC 9(11)V99 VALUE 0.
       PROCEDURE DIVISION.
       NORMALIZE-AMOUNT.
           DISPLAY 'AMOUNT NORMALIZATION UTILITY'
           GOBACK.
       """,
    "utils/AUDITLOG.cbl": """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. AUDITLOG.
       * REMARKS. Shared audit logging utility called by customer,
       *          payments, lending, claims, cards, and treasury flows.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY AUDITREC.
       PROCEDURE DIVISION.
       WRITE-AUDIT-EVENT.
          DISPLAY 'AUDIT EVENT RECORDED'
          GOBACK.
       """,
    # SQL procedures illustrate database-side business operations; the current
    # parser does not ingest .sql files, so they remain source examples only.
    "stored_procs/SP_ACCRUE_ACCOUNT_INTEREST.sql": """
        CREATE PROCEDURE SP_ACCRUE_ACCOUNT_INTEREST (
            IN P_ACCOUNT_ID CHAR(10),
            IN P_INTEREST DECIMAL(9, 2)
        )
        LANGUAGE SQL
        MODIFIES SQL DATA
        BEGIN
            UPDATE ACCOUNT_LEDGER
               SET ACCRUED_INTEREST = ACCRUED_INTEREST + P_INTEREST
             WHERE ACCOUNT_ID = P_ACCOUNT_ID;
        END
        """,
    "stored_procs/SP_POST_PAYMENT.sql": """
        CREATE PROCEDURE SP_POST_PAYMENT (
            IN P_PAYMENT_ID CHAR(12),
            IN P_ACCOUNT_ID CHAR(10),
            IN P_AMOUNT DECIMAL(11, 2)
        )
        LANGUAGE SQL
        MODIFIES SQL DATA
        BEGIN
            UPDATE PAYMENT_LEDGER
               SET BALANCE = BALANCE + P_AMOUNT
             WHERE ACCOUNT_ID = P_ACCOUNT_ID;
            UPDATE PAYMENT
               SET STATUS = 'POST'
             WHERE PAYMENT_ID = P_PAYMENT_ID;
        END
        """,
    "stored_procs/SP_APPLY_LOAN_PAYMENT.sql": """
        CREATE PROCEDURE SP_APPLY_LOAN_PAYMENT (
            IN P_LOAN_ID CHAR(10),
            IN P_AMOUNT DECIMAL(9, 2)
        )
        LANGUAGE SQL
        MODIFIES SQL DATA
        BEGIN
            UPDATE LOAN
               SET PRINCIPAL = PRINCIPAL - P_AMOUNT,
                   STATUS = 'CURRENT'
             WHERE LOAN_ID = P_LOAN_ID;
        END
        """,
    "stored_procs/SP_SETTLE_CARD.sql": """
        CREATE PROCEDURE SP_SETTLE_CARD (
            IN P_CARD_ID CHAR(16),
            IN P_AMOUNT DECIMAL(9, 2)
        )
        LANGUAGE SQL
        MODIFIES SQL DATA
        BEGIN
            UPDATE CARD_ACCOUNT
               SET AVAILABLE_CREDIT = AVAILABLE_CREDIT - P_AMOUNT
             WHERE CARD_ID = P_CARD_ID;
        END
        """,
    "stored_procs/SP_RESERVE_CLAIM.sql": """
        CREATE PROCEDURE SP_RESERVE_CLAIM (
            IN P_CLAIM_ID CHAR(12),
            IN P_RESERVE DECIMAL(9, 2)
        )
        LANGUAGE SQL
        MODIFIES SQL DATA
        BEGIN
            UPDATE CLAIM
               SET RESERVE_AMOUNT = P_RESERVE,
                   STATUS = 'REVIEW'
             WHERE CLAIM_ID = P_CLAIM_ID;
        END
        """,
    "stored_procs/SP_FLAG_TRANSACTION.sql": """
        CREATE PROCEDURE SP_FLAG_TRANSACTION (
            IN P_TRANSACTION_ID CHAR(12),
            IN P_REVIEW_STATUS CHAR(8)
        )
        LANGUAGE SQL
        MODIFIES SQL DATA
        BEGIN
            UPDATE TRANSACTION
               SET REVIEW_STATUS = P_REVIEW_STATUS
             WHERE TRANSACTION_ID = P_TRANSACTION_ID;
        END
        """,
    "stored_procs/SP_REGISTER_CUSTOMER.sql": """
        CREATE PROCEDURE SP_REGISTER_CUSTOMER (
            IN P_CUSTOMER_ID CHAR(8),
            IN P_DOCUMENT_STATUS CHAR(8)
        )
        LANGUAGE SQL
        MODIFIES SQL DATA
        BEGIN
            INSERT INTO CUSTOMER_KYC
                (CUSTOMER_ID, DOCUMENT_STATUS, STATUS)
            VALUES
                (P_CUSTOMER_ID, P_DOCUMENT_STATUS, 'PEND');
        END
        """,
    "stored_procs/SP_UPDATE_CASH_POSITION.sql": """
        CREATE PROCEDURE SP_UPDATE_CASH_POSITION (
            IN P_ACCOUNT_ID CHAR(10),
            IN P_AMOUNT DECIMAL(11, 2)
        )
        LANGUAGE SQL
        MODIFIES SQL DATA
        BEGIN
            UPDATE TREASURY_CASH
               SET AVAILABLE_CASH = AVAILABLE_CASH + P_AMOUNT
             WHERE ACCOUNT_ID = P_ACCOUNT_ID;
        END
        """,
    "stored_procs/SP_WRITE_AUDIT_EVENT.sql": """
        CREATE PROCEDURE SP_WRITE_AUDIT_EVENT (
            IN P_EVENT_ID CHAR(16),
            IN P_EVENT_TYPE CHAR(12),
            IN P_EVENT_TIME TIMESTAMP
        )
        LANGUAGE SQL
        MODIFIES SQL DATA
        BEGIN
            INSERT INTO AUDIT_EVENT (EVENT_ID, EVENT_TYPE, EVENT_TIME)
            VALUES (P_EVENT_ID, P_EVENT_TYPE, P_EVENT_TIME);
        END
        """,
}


def create_mock_cobol_workspace(base_path="./cobol_source"):
  """Write each manifest asset, creating its parent folders as needed.

  Existing files with the same manifest paths are replaced so rerunning setup
  restores a consistent sample without deleting unrelated workspace files.
  """
  for relative_path, content in WORKSPACE_ASSETS.items():
    file_path = os.path.join(base_path, relative_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
      # Remove only the indentation before each embedded asset's first line;
      # the source text itself remains easy to read in this Python manifest.
      file.write(content.lstrip())

  print(
      "Mock COBOL workspace successfully created under "
      f"{base_path} with shared assets across eight business capabilities, "
      "ordered batch jobs, utilities, and stored procedures."
  )


if __name__ == "__main__":
  # Running the script directly populates the documented default workspace.
  create_mock_cobol_workspace()
