"""Parse the Liquidity Provider Program table into a dated snapshot.

The LPP list is a help-centre page with no API and no version history. It
changes -- series have already left it (the June capture carried daily city
high/low temperature ladders that are absent today). So the snapshot is dated
and committed, and every coverage claim cites the snapshot it was computed
from rather than "the LPP list", which is a moving target.

The table below is transcribed verbatim from the fetched page. Group labels
are kept exactly as Kalshi writes them, including the two duplicate "Hourly
Commodities" rows and the two separate "Tennis"/"Golf" rows, because
collapsing them would silently change the provider-count arithmetic.

Source: https://help.kalshi.com/en/articles/15410219-liquidity-provider-program
Fetched: 2026-10-18T21:35:46Z
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
SNAPSHOT_DATE = "2026-10-18"
SOURCE_URL = "https://help.kalshi.com/en/articles/15410219-liquidity-provider-program"
FETCHED_AT = "2026-10-18T21:35:46Z"

# (group label, termination date, provider count)
ROWS = [
    ("WTI (KXWTI, KXWTIW)", "12/31/26", 2),
    ("Truth (KXTRUTHSOCIAL)", "12/31/26", 1),
    ("Primary Daily & Weekly Commodities (BRENT, CORN, GOLD, SILVER, COPPER)", "12/31/26", 1),
    ("Crypto 15min markets", "12/31/26", 2),
    ("Crypto Hourly & Daily", "12/31/26", 1),
    ("Hourly Commodities (KXWTIH, KXGOLDH, KXSILVERH)", "12/31/26", 1),
    ("Rotten Tomatoes", "12/31/26", 1),
    ("Weekly Trump (KXAPRPOTUS, TRUMPACT)", "12/31/26", 1),
    ("Election Primary Voting (KXVOTEPRIMARY, KXPRIMARYTURNOUT)", "12/31/26", 1),
    ("Election Margin of Victory (KXMIDTERMMOV)", "12/31/26", 1),
    ("Album Equivalents (KXALBUMEQUIV)", "12/31/26", 1),
    ("Hourly Weather", "12/31/26", 1),
    ("Hourly Commodities", "12/31/26", 1),
    ("Commodities 15min markets", "12/31/26", 1),
    ("Baseball (KXMLBF5, KXMLBF5TOTAL, KXMLBF5SPREAD, KXMLBF3, KXMLBF3SPREAD, "
     "KXMLBF3TOTAL, KXMLBF7, KXMLBF7SPREAD, KXMLBF7TOTAL, KXMLBTB, KXMLBHRR, KXML, "
     "KXMLBHR, KXMLBHIT, KXMLBTEAMTOTAL, KXMLBRBI, KXMLBEXTRAS, KXMLBRFI)", "12/31/26", 1),
    ("Golf (KXPGAROUNDSCORE, KXPGATOP5, KXPGATOP10, KXPGATOP20, KXPGATOP40, "
     "KXPGAMAKECUT, KXDPWORLDTOURMAKECUT, KXPGAH2H, KXLIVH2H, KXDPWTH2H, "
     "KXPGA3BALL)", "12/31/26", 1),
    ("Tennis (KXATPGTOTAL, KXWTAGTOTAL, KXATPSETWINNER, KXWTASETWINNER)", "12/31/26", 1),
    ("Diesel (KXDIESELD, KXDIESELW, KXDIESELMON)", "12/31/26", 1),
    ("Hourly Temp (KXTEMPMIAH, KXTEMPNYCH, KXTEMPLAH, KXTEMPCHIH)", "12/31/26", 1),
    ("Daily Rain (KXRAIN)", "12/31/26", 1),
    ("AI Share (KXANTHSHARE, KXBABASHARE, KXDEEPSHARE, KXGOOGSHARE, KXOPENSHARE, "
     "KXSTEALTHSHARE, KXTENCENTSHARE, KXXIAOMISHARE)", "12/31/26", 1),
    ("Gas Daily & Weekly (KXAAAGASD, KXAAAGASW)", "12/31/26", 1),
    ("Primary Commodities Daily & Weekly (KXBRENTD, KXBRENTW, KXNATGASD, KXNATGASW, "
     "KXSILVERD, KXSILVERW, KXCOPPERW, KXCOPPERD)", "12/31/26", 1),
    ("Alternate Indices (KXIBOV, KXRUT, KXTSX, KXNIKKEI, KXME, KXKOSPI, KXFTSE, "
     "KXCAC40)", "12/31/26", 1),
    ("Football (KXNFL1H, KXNFL1HSPREAD, KXNFL1HTOTAL, KXNFL2H, KXNFL2HSPREAD, "
     "KXNFL2HTOTAL, KXNFL1Q, KXNFL1QSPREAD, KXNFL1QTOTAL, KXNFL2Q, KXNFL2QSPREAD, "
     "KXNFL2QTOTAL, KXNFL3Q, KXNFL3QSPREAD, KXNFL3QTOTAL, KXNFL4Q, KXNFL4QSPREAD, "
     "KXNFL4QTOTAL, KXNFLOT, KXNFLTOTALTD, KXNFLFIRSTTDTEAM, KXNFLTEAMFIRSTTD, "
     "KXNFLWINMARGIN, KXNFLTEAMTD, KXNFLFG, KXNFL1HFT, KXNFLPASSTDS, KXNFLPASSYDS, "
     "KXNFLTD, KXNFL1QBTTS, KXNFL2QBTTS, KXNFL3QBTTS, KXNFL4QBTTS)", "12/31/26", 1),
    ("Esports (KXCS2MAP, KXDOTA2MAP, KXLOLMAP, KXVALORANTMAP, KXCODMAP, KXR6MAP, "
     "KXCS2TOTALMAPS, KXDOTA2TOTALMAPS, KXLOLTOTALMAPS, KXVALORANTTOTALMAPS, "
     "KXCODTOTALMAPS)", "12/31/26", 1),
    ("Tennis (KXATPGSPREAD, KXATPEXACTMATCH, KXWTAEXACTMATCH, KXATPTOTALSETS)", "12/31/26", 1),
    ("Golf (KXPGAR1TOP5, KXPGAR1TOP10, KXPGAR1TOP20, KXPGAR2TOP5, KXPGAR2TOP10, "
     "KXPGAR3TOP5, KXPGAR3TOP10, KXPGALOWSCORE, KXPGACUTLINE, KXPGAWINNERREGION, "
     "KXPGAH2H, KXDPWTH2H, KXLIVH2H, KXPGA5BALL, KXPGAPLAYERCAT)", "12/31/26", 1),
    ("FX 15min markets", "12/31/26", 2),
    ("AAVE (KXAAVEPERP)", "12/31/26", 3),
    ("ADA (KXADAPERP)", "12/31/26", 3),
    ("BCH (KXBCHPERP)", "12/31/26", 6),
    ("BNB (KXBNBPERP)", "12/31/26", 3),
    ("BTC (KXBTCPERP)", "12/31/26", 6),
    ("DOGE (KXDOGEPERP)", "12/31/26", 6),
    ("ETH (KXETHPERP)", "12/31/26", 6),
    ("Gold (KXGOLDPERP)", "12/31/26", 4),
    ("HYPE (KXHYPEPERP)", "12/31/26", 6),
    ("SHIB (KXKSHIBPERP)", "12/31/26", 6),
    ("LINK (KXLINKPERP)", "12/31/26", 6),
    ("LTC (KXLTCPERP)", "12/31/26", 6),
    ("NEAR (KXNEARPERP)", "12/31/26", 3),
    ("Silver (KXSILVERPERP)", "12/31/26", 4),
    ("SOL (KXSOLPERP)", "12/31/26", 6),
    ("SUI (KXSUIPERP)", "12/31/26", 6),
    ("VVV (KXVVVPERP)", "12/31/26", 3),
    ("WLD (KXWLDPERP)", "12/31/26", 3),
    ("XRP (KXXRPPERP)", "12/31/26", 6),
    ("ZEC (KXZECPERP)", "12/31/26", 5),
    ("Platinum (KXPLATINUMPERP)", "12/31/26", 4),
    ("Palladium (KXPALLADIUMPERP)", "12/31/26", 3),
    ("Financial Indices (KXINXU, KXNASDAQ100U, KXINX, KXNASDAQ100, KXINXDUD, "
     "KXNASDAQDUD)", "12/31/26", 1),
]

# Rows whose coverage is described in prose, not tickers. These CANNOT be
# resolved to series programmatically; a ladder matching one of these
# descriptions must be treated as "coverage unknown", never as uncovered.
# Being wrong in this direction is the expensive mistake: it would put us
# head-to-head with a designated provider while believing the series is empty.
PROSE_ROWS = {
    "Crypto 15min markets",
    "Crypto Hourly & Daily",
    "Rotten Tomatoes",
    "Hourly Weather",
    "Hourly Commodities",
    "Commodities 15min markets",
    "FX 15min markets",
    "Primary Daily & Weekly Commodities (BRENT, CORN, GOLD, SILVER, COPPER)",
}

TICKER_RE = re.compile(r"\b(KX[A-Z0-9]+|TRUMPACT)\b")


def parse():
    explicit = {}       # ticker -> {"groups": [...], "providers": max}
    prose = []
    for label, term, providers in ROWS:
        tickers = TICKER_RE.findall(label)
        if label in PROSE_ROWS or not tickers:
            prose.append({"group": label, "termination": term,
                          "provider_count": providers,
                          "tickers_named": tickers})
            # a prose row may still name tickers (Primary Daily & Weekly
            # Commodities names bare words, not KX tickers) -- record them
            # but do not treat the row as exhaustive
        if not tickers:
            continue
        for t in tickers:
            e = explicit.setdefault(t, {"groups": [], "provider_count": 0})
            e["groups"].append(label)
            e["provider_count"] = max(e["provider_count"], providers)
    return explicit, prose


def main():
    explicit, prose = parse()
    out = {
        "snapshot_date": SNAPSHOT_DATE,
        "source_url": SOURCE_URL,
        "fetched_at": FETCHED_AT,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "n_rows": len(ROWS),
        "n_explicit_tickers": len(explicit),
        "n_prose_rows": len(prose),
        "provider_count_by_ticker": {k: v["provider_count"] for k, v in sorted(explicit.items())},
        "groups_by_ticker": {k: v["groups"] for k, v in sorted(explicit.items())},
        "prose_rows": prose,
        "rows": [{"group": a, "termination": b, "provider_count": c} for a, b, c in ROWS],
    }
    p = HERE / ("lpp_%s.json" % SNAPSHOT_DATE)
    p.write_text(json.dumps(out, indent=2) + "\n")
    print("wrote %s" % p)
    print("rows=%d explicit_tickers=%d prose_rows=%d"
          % (len(ROWS), len(explicit), len(prose)))
    print("total provider slots (explicit rows): %d"
          % sum(c for _, _, c in ROWS))


if __name__ == "__main__":
    main()
