import re
import sys
from typing import List, Sequence, Tuple


def _make_2d(rows: int, cols: int, value=0.0):
    return [[value for _ in range(cols + 1)] for _ in range(rows + 1)]


def _parse_numeric_input(text: str) -> List[float]:
    tokens = re.findall(r"[+-]?\d+(?:\.\d+)?", text)
    return [float(tok) for tok in tokens]


class _FixedReader:
    def __init__(self, text: str) -> None:
        self._text = text
        self._idx = 0

    def _read_fixed(self, width: int) -> str:
        chars = []
        while len(chars) < width and self._idx < len(self._text):
            ch = self._text[self._idx]
            self._idx += 1
            if ch in ("\r", "\n"):
                continue
            chars.append(ch)
        return "".join(chars)

    def read_i3_1x(self, count: int) -> List[int]:
        out: List[int] = []
        for _ in range(count):
            out.append(int(self._read_fixed(3).strip() or "0"))
            _ = self._read_fixed(1)  # separator
        return out

    def read_f4_2(self, count: int) -> List[float]:
        out: List[float] = []
        for _ in range(count):
            out.append(float(self._read_fixed(4).strip() or "0"))
        return out

    def read_i1_1x(self, count: int) -> List[int]:
        out: List[int] = []
        for _ in range(count):
            # Fortran I1,1X keeps one-char value and one-char separator.
            val = self._read_fixed(1).strip()
            out.append(int(val or "0"))
            _ = self._read_fixed(1)
        return out


def _parse_fortran_fixed_input(text: str) -> List[float]:
    reader = _FixedReader(text)
    values: List[float] = []
    values.extend(float(v) for v in reader.read_i3_1x(10))   # ICH
    values.extend(reader.read_f4_2(20))                      # XSC
    values.extend(float(v) for v in reader.read_i3_1x(20))   # JET
    values.extend(float(v) for v in reader.read_i1_1x(2))    # NA, IO
    return values


def _read_inputs(values: Sequence[float]) -> Tuple[List[int], List[float], List[int], int, int]:
    NCH = 10
    NTP = 20
    NPR = 20
    needed = NCH + NTP + NPR + 2
    if len(values) < needed:
        raise ValueError(f"Not enough input values: need at least {needed}, got {len(values)}")

    ptr = 0
    ich = [0] * (NCH + 1)
    for i in range(1, NCH + 1):
        ich[i] = int(values[ptr])
        ptr += 1

    xsc = [0.0] * (NTP + 1)
    for lt in range(1, NTP + 1):
        xsc[lt] = float(values[ptr])
        ptr += 1

    jet = [0] * (NPR + 1)
    for j in range(1, NPR + 1):
        jet[j] = int(values[ptr])
        ptr += 1

    na = int(values[ptr])
    ptr += 1
    io = int(values[ptr])

    return ich, xsc, jet, na, io


def run_simulation(values: Sequence[float]) -> None:
    NTP = 20
    NCH = 10
    NPR = 20
    NDM = 10

    ICH, XSC, JET, NA, IO = _read_inputs(values)

    JF = [0] * (NPR + 1)
    XERC = [0.0] * (NCH + 1)
    XEE = [0.0] * (NCH + 1)
    JFF = [0] * (NPR + 1)
    XERP = [0.0] * (NPR + 1)
    JPS = [0] * (NPR + 1)
    ICS = [0] * (NCH + 1)
    KDC = [0] * (NDM + 1)
    KDCW = [0] * (NDM + 1)

    JIA = _make_2d(NPR, NCH, value=0)
    IKA = _make_2d(NCH, NDM, value=0)
    KABC = _make_2d(NTP, NCH, value=0)
    KBBC = _make_2d(NTP, NDM, value=0)
    KCBC = _make_2d(NTP, NPR, value=0)
    XEA = _make_2d(NDM, NTP, value=0.0)

    print(f"DEC.MAKER MOVEMENT CONDITION (NA) IS {NA}")

    for IL in range(1, 4):
        IB = IL - 1
        for JAB in range(1, 4):
            JA = JAB - 1
            for JDB in range(1, 4):
                JD = JDB - 1
                for JEB in range(1, 4):
                    JE = JEB - 1
                    XR = 0.0
                    XS = 0.0
                    KS = 0

                    for i in range(1, NCH + 1):
                        XERC[i] = 1.1
                        XEE[i] = 0.0
                        ICS[i] = 0

                    for k in range(1, NDM + 1):
                        KDC[k] = 0
                        KDCW[k] = 0

                    for j in range(1, NPR + 1):
                        XERP[j] = IL * 1.1
                        JF[j] = 0
                        JFF[j] = 0
                        JPS[j] = 0

                    for i in range(1, NCH + 1):
                        for j in range(1, NDM + 1):
                            IKA[i][j] = 1
                            if JD == 1 and i < j:
                                IKA[i][j] = 0
                            elif JD == 2 and j != i:
                                IKA[i][j] = 0

                    for i in range(1, NPR + 1):
                        for j in range(1, NCH + 1):
                            JIA[i][j] = 0
                            if JA == 1:
                                if (i - j) <= (i // 2):
                                    JIA[i][j] = 1
                            elif JA == 2:
                                if i == (2 * j):
                                    JIA[i][j] = 1
                                    if i - 1 >= 1:
                                        JIA[i - 1][j] = 1
                            else:
                                JIA[i][j] = 1

                    for i in range(1, NDM + 1):
                        for j in range(1, NTP + 1):
                            XEA[i][j] = 0.55
                            # In fortran.f this condition appears as JF.EQ.1 (likely typo).
                            if JE == 1:
                                continue
                            xxa = float(i)
                            if JE == 0:
                                XEA[i][j] = xxa / 10.0
                            else:
                                XEA[i][j] = (11.0 - xxa) / 10.0

                    for LT in range(1, NTP + 1):
                        for i in range(1, NCH + 1):
                            if ICH[i] == LT:
                                ICS[i] = 1

                        # fortran.f has "DO 110 J = I,NPR", treated as typo and ported as 1..NPR.
                        for j in range(1, NPR + 1):
                            if JET[j] == LT:
                                JPS[j] = 1

                        for j in range(1, NPR + 1):
                            if JPS[j] != 1:
                                continue

                            if NA in (2, 4) and JF[j] != 0:
                                JFF[j] = JF[j]
                                continue

                            S = 1_000_000.0
                            for i in range(1, NCH + 1):
                                if ICS[i] != 1:
                                    continue
                                if JIA[j][i] == 0:
                                    continue
                                if JF[j] in (0, i):
                                    trial = XERC[i] - XEE[i]
                                else:
                                    trial = XERP[j] + XERC[i] - XEE[i]
                                if trial >= S:
                                    continue
                                S = trial
                                JFF[j] = i

                        for j in range(1, NPR + 1):
                            JF[j] = JFF[j]
                            JFF[j] = 0

                        LTT = LT - 1
                        if LT == 1:
                            LTT = 1

                        for k in range(1, NDM + 1):
                            if NA in (3, 4) and KDC[k] != 0:
                                KDCW[k] = KDC[k]
                                continue

                            S = 1_000_000.0
                            for i in range(1, NCH + 1):
                                if ICS[i] != 1:
                                    continue
                                if IKA[i][k] == 0:
                                    continue
                                # fortran.f has XFRC(I), treated as XERC(I).
                                if KDC[k] in (0, i):
                                    trial = XERC[i] - XEE[i]
                                else:
                                    trial = XERC[i] - XEE[i] - (XEA[k][LTT] * XSC[LTT])
                                if trial >= S:
                                    continue
                                S = trial
                                KDCW[k] = i

                        for k in range(1, NDM + 1):
                            KDC[k] = KDCW[k]
                            if KDC[k] == 0:
                                XR += XEA[k][LT] * XSC[LT]
                                KS += 1
                            KDCW[k] = 0

                        for i in range(1, NCH + 1):
                            if ICS[i] == 0:
                                continue
                            XERC[i] = 0.0
                            XEE[i] = 0.0
                            for j in range(1, NPR + 1):
                                if JPS[j] == 1 and JF[j] == i:
                                    XERC[i] += XERP[j]
                            for k in range(1, NDM + 1):
                                if IKA[i][k] != 0 and KDC[k] == i:
                                    XEE[i] += XSC[LT] * XEA[k][LT]

                        for i in range(1, NCH + 1):
                            if ICS[i] != 1:
                                continue
                            if XERC[i] > XEE[i]:
                                continue
                            XS += XEE[i] - XERC[i]
                            ICS[i] = 2
                            for j in range(1, NPR + 1):
                                if JF[j] == i:
                                    JPS[j] = 2
                            if NA in (3, 4):
                                for k in range(1, NDM + 1):
                                    if KDC[k] == i:
                                        KDCW[k] = 1

                        for i in range(1, NCH + 1):
                            KABC[LT][i] = ICS[i]

                        for k in range(1, NDM + 1):
                            KBBC[LT][k] = KDC[k]
                            if KDCW[k] != 0:
                                KDC[k] = 0
                            KDCW[k] = 0

                        for j in range(1, NPR + 1):
                            KCBC[LT][j] = JF[j]
                            if JPS[j] == 0:
                                KCBC[LT][j] = -1
                            elif JPS[j] != 1:
                                KCBC[LT][j] = 1000

                    KZ = 0
                    KY = 0
                    KX = 0
                    KW = 0
                    KV = 0
                    KU = 0
                    KT = 0

                    for i in range(1, NTP + 1):
                        for j in range(1, NCH + 1):
                            if KABC[i][j] != 1:
                                continue
                            KY += 1
                            if i == NTP:
                                KZ += 1

                    for i in range(2, NTP + 1):
                        for j in range(1, NDM + 1):
                            if KBBC[i][j] != KBBC[i - 1][j]:
                                KX += 1

                    for i in range(1, NTP + 1):
                        for j in range(1, NPR + 1):
                            val = KCBC[i][j]
                            if val == 0:
                                KU += 1
                            elif val == -1:
                                continue
                            elif val == 1000:
                                if i == NTP:
                                    KW += 1
                            else:
                                KT += 1

                    KW = NPR - KW

                    for i in range(2, NTP + 1):
                        for j in range(1, NPR + 1):
                            if KCBC[i][j] != KCBC[i - 1][j]:
                                KV += 1

                    print(
                        "LOAD={:1d} PR.ACC.={:1d} DEC.STR.={:1d} EN.DIST.={:1d} "
                        "STATS 1-10 {:5d}{:5d}{:5d}{:5d}{:5d}{:5d}{:5d}{:5d} {:6.2f}{:6.2f}".format(
                            IB,
                            JA,
                            JD,
                            JE,
                            KZ,
                            KY,
                            KX,
                            KW,
                            KV,
                            KU,
                            KT,
                            KS,
                            XR,
                            XS,
                        )
                    )

                    if IO != 2:
                        continue

                    print(" CHOICE ACTIVATION HISTORY".ljust(46) + "DEC.MAKER ACTIVITY HISTORY")
                    print(
                        " 0=INACTIVE, 1=ACTIVE, 2=MADE".ljust(46)
                        + "0=INACTIVE, X=WORKING ON CHOICE X"
                    )
                    for LT in range(1, NTP + 1):
                        left = "".join(f"{KABC[LT][j]:2d}" for j in range(1, NCH + 1))
                        right = "".join(f"{KBBC[LT][j]:2d}" for j in range(1, NDM + 1))
                        print(f"{LT:2d} {left}    {LT:2d} {right}")

                    print(" PROBLEM HISTORY: -1=NOT ENTERED, 0=UNATTACHED, X=ATTACHED, 1000=SOLVED")
                    for LT in range(1, NTP + 1):
                        row = "".join(f"{KCBC[LT][j]:3d}" for j in range(1, NPR + 1))
                        print(f"{LT:2d} {row}")


def main() -> None:
    text = sys.stdin.read()
    if not text.strip():
        return
    values = _parse_numeric_input(text)
    # Support classic Fortran fixed-width input such as "008.005...." and packed F4.2.
    if len(values) < 52:
        values = _parse_fortran_fixed_input(text)
    run_simulation(values)


if __name__ == "__main__":
    main()
