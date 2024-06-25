# SPDX-FileCopyrightText: 2024 Lukas Schrangl <lukas.schrangl@boku.ac.at>
# SPDX-License-Identifier: BSD-3-Clause
#
# SPDX-FileCopyrightText: Copyright (c) 2023 Justin Gerber
# SPDX-License-Identifier: MIT
#
# This is a collection of relevant parts of the `sciform` package

from decimal import Decimal
from enum import Enum


def format_val(val: float | Decimal, n_digits: int):
    val_r = round_val(val, n_digits)
    return f"{val_r:f}"


def round_val(val: float | Decimal, n_digits: int):
    val = Decimal(val)
    round_digit = get_round_dec_place(val, RoundModeEnum.SIG_FIG, n_digits)
    return round(val, -round_digit)


def format_val_unc(
    val: float | Decimal, unc: float | Decimal, n_digits: int, pdg_sig_figs: bool
):
    val_r, unc_r, _ = round_val_unc(val, unc, n_digits, pdg_sig_figs)
    return f"{val_r:f} ± {unc_r:f}"


def round_val_unc(
    val: float | Decimal, unc: float | Decimal, n_digits: int, pdg_sig_figs: bool
):
    val = Decimal(val)
    unc = Decimal(unc)

    # We round twice in case the first rounding changes the digits place
    # to which we need to round. E.g. rounding 999.999 ± 123.456 to two
    # significant figures will lead to 1000.000 ± 0120.000 on the first
    # pass, but we must re-round to get 1000.000 ± 0100.000.
    val_rounded, unc_rounded, _ = _do_round_val_unc(
        val,
        unc,
        n_digits,
        use_pdg_sig_figs=pdg_sig_figs,
    )
    return _do_round_val_unc(
        val_rounded,
        unc_rounded,
        n_digits,
        use_pdg_sig_figs=pdg_sig_figs,
    )


def get_bottom_dec_place(num: Decimal) -> int:
    """Get the decimal place of a decimal's least significant digit."""
    if not num.is_finite():
        return 0
    _, _, exp = num.normalize().as_tuple()
    return exp


def get_top_dec_place(num: Decimal) -> int:
    """Get the decimal place of a decimal's most significant digit."""
    if not num.is_finite() or num == 0:
        return 0
    _, digits, exp = num.normalize().as_tuple()
    return len(digits) + exp - 1


class SentinelMeta(type):
    """Sentinel metaclass, __repr__ returns class name."""

    def __repr__(cls) -> str:
        return cls.__name__


class AutoDigits(metaclass=SentinelMeta):
    """
    Flag for auto ndigits calculation mode.

    In both sig fig and ndigits round modes this auto ndigits
    option chooses the ndigits so that the least significant digit of
    the input number will be displayed.
    For example the number 123.456789 would be displayed with either 9
    significant figures or 6 digits past the decimal point so that in
    either case all digits are shown.

    When used with sig fig rounding and in combination with the
    ``pdg_sig_figs`` option, the number of significant figures will be
    chosen to be one or two in accordance with the Particle Data Group
    algorithm.
    """


class RoundModeEnum(str, Enum):
    """Round mode Enum."""

    SIG_FIG = "sig_fig"
    DEC_PLACE = "dec_place"


def get_pdg_round_digit(num: Decimal) -> int:
    """
    Determine the PDG rounding decimal place to which to round.

    Calculate the appropriate decimal place to which to round  according
    to the particle data group 3-5-4 rounding rules.

    See
    https://pdg.lbl.gov/2010/reviews/rpp2010-rev-rpp-intro.pdf
    Section 5.2
    """
    if not num.is_finite():
        msg = f"num must be finite, not {num}."
        raise ValueError(msg)

    top_dec_place = get_top_dec_place(num)

    # Bring num to be between 100 and 1000.
    num_top_three_digs = num * Decimal(10) ** (Decimal(2) - Decimal(top_dec_place))
    num_top_three_digs = num_top_three_digs.quantize(1, rounding="ROUND_FLOOR")
    new_top_dec_place = get_top_dec_place(num_top_three_digs)
    num_top_three_digs = num_top_three_digs * 10 ** (2 - new_top_dec_place)
    if 100 <= num_top_three_digs <= 354:
        round_digit = top_dec_place - 1
    elif 355 <= num_top_three_digs <= 949:
        round_digit = top_dec_place
    elif 950 <= num_top_three_digs <= 999:
        """
        Here we set the round digit equal to the top digit. But since
        the top three digits are >= 950 this means they will be rounded
        up to 1000. So with round digit set to the top digit this will
        correspond to displaying two digits of uncertainty: "10".
        e.g. 123.45632 +/- 0.987 would be rounded as 123.5 +/- 1.0.
        """
        round_digit = top_dec_place
    else:  # pragma: no cover
        msg = f"Unable to determine PDG rounding decimal place for {num}"
        raise ValueError(msg)

    return round_digit


def get_round_dec_place(
    num: Decimal,
    round_mode: RoundModeEnum,
    ndigits: int | type(AutoDigits),
    *,
    pdg_sig_figs: bool = False,
) -> int:
    """Get the decimal place to which to round."""
    # TODO: Handle nan and inf
    if round_mode is RoundModeEnum.SIG_FIG:
        if pdg_sig_figs:
            round_digit = get_pdg_round_digit(num)
        elif ndigits is AutoDigits:
            round_digit = get_bottom_dec_place(num)
        else:
            round_digit = get_top_dec_place(num) - (ndigits - 1)
    elif round_mode is RoundModeEnum.DEC_PLACE:
        round_digit = get_bottom_dec_place(num) if ndigits is AutoDigits else -ndigits
    else:
        msg = f"Unhandled round mode: {round_mode}."
        raise ValueError(msg)
    return round_digit


def _do_round_val_unc(
    val: Decimal,
    unc: Decimal,
    ndigits: int | type[AutoDigits],
    *,
    use_pdg_sig_figs: bool = False,
) -> tuple[Decimal, Decimal, int]:
    """Simultaneously round the value and uncertainty."""
    if unc.is_finite() and unc != 0:
        round_digit = get_round_dec_place(
            unc,
            RoundModeEnum.SIG_FIG,
            ndigits,
            pdg_sig_figs=use_pdg_sig_figs,
        )
        unc_rounded = round(unc, -round_digit)
        if val.is_finite():
            val_rounded = round(val, -round_digit)
        else:
            val_rounded = val
    elif val.is_finite():
        round_digit = get_round_dec_place(
            val,
            RoundModeEnum.SIG_FIG,
            ndigits,
            pdg_sig_figs=False,
        )
        unc_rounded = unc
        val_rounded = round(val, -round_digit)
    else:
        round_digit = 0
        unc_rounded = unc
        val_rounded = val

    return val_rounded, unc_rounded, round_digit
