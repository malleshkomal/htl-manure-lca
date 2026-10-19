C     DECOMPOS yield calculator (thesis Table 3.2.1, adapted from Refs. [24-25][7])
C     Imported variables (Aspen Calculator block):
C       WATER  = PROXANAL moisture of stream MANURE, wt%
C       PROX   = PROXANAL vector of MANURE (PROX(2) = fixed carbon)
C       ULT    = ULTANAL vector of MANURE
C                ULT(1)=ash ULT(2)=C ULT(3)=H ULT(4)=N ULT(5)=Cl ULT(6)=S ULT(7)=O
C     Exported variables: mass yields of block DECOMPOS
      FACT  = (100 - WATER) / 100
      H2O   = WATER / 100
      CHAR  = PROX(2) / 100 * FACT
      ASH   = ULT(1)  / 100 * FACT
      O2    = ULT(7)  / 100 * FACT
      H2    = ULT(3)  / 100 * FACT
      N2    = ULT(4)  / 100 * FACT
      C     = (ULT(2) / 100 * FACT) - CHAR
C     Not in the printed table: add sulfur so the yields sum to 1
      S     = ULT(6)  / 100 * FACT
