import os


def create_mock_cobol_workspace():
  os.makedirs("./cobol_source/jcl", exist_ok=True)
  os.makedirs("./cobol_source/programs", exist_ok=True)
  os.makedirs("./cobol_source/copybooks", exist_ok=True)
  os.makedirs("./cobol_source/utils", exist_ok=True)

  # 1. JCL Job Files
  with open("./cobol_source/jcl/WEEKLY_BILLING.jcl", "w") as f:
    f.write("""
        //WEEKLY01 JOB (ACCT100),'WEEKLY BILLING RUN',CLASS=A,MSGCLASS=X
        //STEP10 EXEC PGM=CUSTUPD0
        //STEPLIB DD DSN=PROD.LOADLIB,DISP=SHR
        //CUSTFILE DD DSN=PROD.CUSTOMER.MASTER,DISP=SHR
        //RPTFILE  DD DSN=PROD.BILLING.REPORT,DISP=(NEW,CATLG)
        """)

  with open("./cobol_source/jcl/MONTH_END.jcl", "w") as f:
    f.write("""
        //MONThend JOB (ACCT100),'MONTHLY INTEREST RUN',CLASS=A,MSGCLASS=X
        //STEP20 EXEC PGM=INTRCALC
        //STEPLIB DD DSN=PROD.LOADLIB,DISP=SHR
        //CUSTFILE DD DSN=PROD.CUSTOMER.MASTER,DISP=SHR
        //INTFILE  DD DSN=PROD.INTEREST.LOG,DISP=(NEW,CATLG)
        """)

  # 2. COBOL Program Files
  with open("./cobol_source/programs/CUSTUPD0.cbl", "w") as f:
    f.write("""
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTUPD0.
       * AUTHOR. LEGACY TEAM.
       * REMARKS. Updates customer tier status based on yearly expenditure 
       *          and invokes interest computation routines.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-CONTROL-VARS.
          05 WS-EOF-SW       PIC X(01) VALUE 'N'.
       COPY CUSTREC.
       PROCEDURE DIVISION.
       MAIN-LOGIC.
            PERFORM OPEN-FILES.
            PERFORM PROCESS-RECORDS UNTIL WS-EOF-SW = 'Y'.
            PERFORM CLOSE-FILES.
            STOP RUN.
       PROCESS-RECORDS.
            READ CUSTFILE INTO CUSTOMER-RECORD.
            IF CUST-BALANCE > 10000.00
               MOVE 'VIP' TO CUST-TIER
            ELSE
               MOVE 'REG' TO CUST-TIER
            END-IF.
       """)

  with open("./cobol_source/programs/INTRCALC.cbl", "w") as f:
    f.write("""
       IDENTIFICATION DIVISION.
       PROGRAM-ID. INTRCALC.
       * AUTHOR. LEGACY TEAM.
       * REMARKS. Calculates monthly compound interest for VIP customers
       *          based on their account balance and rate tables.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-INTEREST-RATE    PIC V999 VALUE 0.045.
       01 WS-CALC-AMOUNT      PIC 9(07)V99 VALUE 0.00.
       COPY CUSTREC.
       COPY ACCTREC.
       PROCEDURE DIVISION.
       CALCULATE-INTEREST.
            IF CUST-TIER = 'VIP'
               COMPUTE WS-CALC-AMOUNT = CUST-BALANCE * WS-INTEREST-RATE
               ADD WS-CALC-AMOUNT TO CUST-BALANCE
            END-IF.
       """)

  # 3. Copybook Files
  with open("./cobol_source/copybooks/CUSTREC.cpy", "w") as f:
    f.write("""
       01 CUSTOMER-RECORD.
          05 CUST-ID       PIC X(08).
          05 CUST-NAME     PIC X(30).
          05 CUST-BALANCE  PIC 9(07)V99.
          05 CUST-TIER     PIC X(03).
       """)

  with open("./cobol_source/copybooks/ACCTREC.cpy", "w") as f:
    f.write("""
       01 ACCOUNT-LEDGER-RECORD.
          05 ACCT-ID       PIC X(10).
          05 ACCT-LEDGER   PIC X(04).
          05 ACCT-ACCRUED  PIC 9(05)V99.
       """)

  print(
      "Mock COBOL workspace successfully expanded under ./cobol_source/ with"
      " multi-program dependencies!"
  )


if __name__ == "__main__":
  create_mock_cobol_workspace()