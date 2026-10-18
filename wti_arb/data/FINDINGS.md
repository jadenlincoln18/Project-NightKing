# FINDINGS - Kalshi commodity ladder history

Generated 2026-09-10T18:36:27+00:00 from `data` (period = 1 min). Numbers come from the manifest and the markets/events tables, not from logs.

Manifest: ok=52378 empty=3789 not_found=0 error=0, candles=58,917,335.

## Per series

| series | title | settles on | ladder | events | markets | candles | quoted window | tradeable window |
|---|---|---|---|---:|---:|---:|---|---|
| KXWTI | WTI oil on day | ICE | RANGE | 838 | 12348 | 8,892,333 | 2022-09..2024-06, 2026-03..2026-09 | 2022-09..2022-12, 2023-02..2023-03, 2026-03..2026-09 |
| KXNATGASD | Natural Gas Daily | Pyth, Trading Economics - Natural Gas, P | CUMUL | 92 | 7762 | 5,094,817 | 2026-03..2026-09 | 2026-05..2026-07, 2026-09..2026-09 |
| KXSILVERD | Silver daily | Pyth - Silver, Trading Economics - Silve | CUMUL | 95 | 3911 | 3,894,687 | 2026-03..2026-09 | 2026-04..2026-08 |
| KXGOLDD | Gold Daily | Pyth - Gold, Trading Economics - Gold, T | CUMUL | 95 | 3873 | 3,882,597 | 2026-03..2026-09 | 2026-04..2026-09 |
| KXBRENTD | Brent Oil Daily | Pyth, Trading Economics - Brent crude oi | CUMUL | 97 | 2503 | 2,660,847 | 2026-03..2026-09 | 2026-03..2026-09 |
| KXGOLDW | Gold Weekly price  | Pyth - Gold, ICE, Trading Economics - Go | CUMUL | 26 | 1050 | 2,568,873 | 2026-03..2026-09 | 2026-03..2026-09 |
| KXCOPPERD | Daily Copper | Pyth, Trading Economics - Copper Futures | CUMUL | 94 | 4378 | 2,558,031 | 2026-03..2026-09 | 2026-06..2026-06, 2026-08..2026-09 |
| KXGOLDMON | Gold Monthly Price | Pyth - Gold, ICE, Trading Economics - Go | CUMUL | 8 | 330 | 2,328,764 | 2026-02..2026-09 | 2026-02..2026-08 |
| KXWTIW | WTI oil weekly range | ICE | RANGE | 201 | 3119 | 2,311,548 | 2022-09..2024-08, 2025-11..2026-09 | 2022-09..2022-11, 2023-02..2023-02, 2024-04..2024-04, 2025-12..2026-09 |
| KXSILVERMON | Silver Monthly Price | Pyth - Silver, Trading Economics - Silve | CUMUL | 7 | 280 | 2,185,738 | 2026-03..2026-09 | 2026-03..2026-08 |
| KXSILVERW | Silver Weekly Price | Pyth - Silver, Trading Economics - Silve | CUMUL | 26 | 1050 | 2,037,228 | 2026-03..2026-09 | 2026-03..2026-03, 2026-05..2026-07 |
| KXCOPPERW | Copper Weekly Price | Pyth | CUMUL | 21 | 870 | 1,884,856 | 2026-04..2026-09 | 2026-04..2026-04, 2026-06..2026-09 |
| KXAAAGASM | US gas price | AAA | CUMUL | 37 | 470 | 1,545,017 | 2023-12..2023-12, 2024-02..2024-02, 2024-04..2026-09 | 2023-12..2023-12, 2024-02..2024-02, 2024-04..2025-01, 2025-03..2026-09 |
| KXBRENTMON | Brent Monthly | Pyth, Trading Economics - Brent crude oi | CUMUL | 6 | 150 | 1,316,932 | 2026-04..2026-09 | 2026-04..2026-09 |
| KXBRENTW | Brent Oil | Pyth, Trading Economics - Brent crude oi | CUMUL | 24 | 520 | 1,316,294 | 2026-03..2026-09 | 2026-03..2026-09 |
| KXAAAGASW | US gas price up | AAA | CUMUL | 137 | 927 | 1,171,423 | 2024-07..2024-08, 2024-10..2026-09 | 2024-07..2024-08, 2024-10..2026-09 |
| KXCOPPERMON | Copper Monthly Price | Pyth, Trading Economics - Copper Futures | CUMUL | 7 | 290 | 1,133,970 | 2026-03..2026-09 | 2026-04..2026-04, 2026-06..2026-09 |
| KXWTIMAX | WTI oil high | ICE | CUMUL | 7 | 135 | 1,070,153 | 2023-11..2023-12, 2024-12..2024-12, 2025-09..2025-09, 2025-12..2025-12, 2026-03..2026-04, 2026-07..2026-09 | 2023-11..2023-12, 2024-12..2024-12, 2025-09..2025-09, 2025-12..2025-12, 2026-03..2026-04, 2026-07..2026-09 |
| KXNATGASW | Natural Gas Weekly | Pyth, Trading Economics - Natural Gas | CUMUL | 23 | 949 | 1,037,258 | 2026-04..2026-09 | 2026-06..2026-07, 2026-09..2026-09 |
| KXNATGASMON | Natural Gas Monthly | Pyth, Trading Economics - Natural Gas | CUMUL | 6 | 240 | 740,995 | 2026-04..2026-09 | 2026-04..2026-04, 2026-07..2026-07 |
| KXAAAGASD | US gas price up | AAA | CUMUL | 195 | 3057 | 682,814 | 2026-03..2026-09 | 2026-03..2026-09 |
| KXWTIMIN | WTI oil low | ICE | CUMUL | 7 | 83 | 436,785 | 2023-03..2023-03, 2023-12..2023-12, 2024-09..2024-09, 2024-12..2024-12, 2025-11..2025-12, 2026-04..2026-04, 2026-06..2026-09 | 2023-03..2023-03, 2023-12..2023-12, 2024-12..2024-12, 2025-11..2025-12, 2026-04..2026-04, 2026-06..2026-09 |
| KXUSGASCPI | US gasoline CPI in [month] | FRED, Trading Economics | CUMUL | 6 | 129 | 307,392 | 2026-04..2026-09 | 2026-04..2026-09 |
| KXAAAGASMAXCA | California highest gas price yearly | AAA | CUMUL | 4 | 33 | 272,406 | 2023-12..2023-12, 2024-07..2024-07, 2024-12..2024-12, 2025-12..2025-12, 2026-02..2026-04, 2026-09..2026-09 | 2023-12..2023-12, 2024-07..2024-07, 2024-12..2024-12, 2025-12..2025-12, 2026-02..2026-04 |
| KXGOLDDIRY | GOLDDIRY | Pyth - Gold | CUMUL | 1 | 13 | 230,859 | 2026-09..2026-09 | none |
| KXAAAGASMINCA | California lowest gas price yearly | AAA | CUMUL | 4 | 12 | 226,571 | 2023-11..2023-11, 2024-11..2024-12, 2025-07..2025-07, 2025-12..2026-01, 2026-09..2026-09 | 2023-11..2023-11, 2024-11..2024-12, 2025-07..2025-07, 2025-12..2026-01 |
| KXOIL | Price of oil monthly | Energy Information Administration | CUMUL | 10 | 28 | 225,762 | 2022-03..2022-08 | 2022-03..2022-08 |
| KXAAAGASMAXTX | Texas highest gas price yearly | AAA | CUMUL | 4 | 27 | 223,577 | 2024-12..2024-12, 2025-12..2025-12, 2026-02..2026-05, 2026-09..2026-09 | 2024-12..2024-12, 2025-12..2025-12, 2026-02..2026-05 |
| KXAAAGASMAX | US highest gas price yearly | AAA | CUMUL | 4 | 20 | 214,624 | 2024-12..2024-12, 2026-03..2026-05, 2026-09..2026-09 | 2024-12..2024-12, 2026-03..2026-05 |
| KXNGASMAX | Natural gas price peak | Energy Information Administration | CUMUL | 5 | 21 | 207,483 | 2024-01..2024-01, 2025-01..2025-01, 2025-11..2025-12, 2026-09..2026-09 | 2025-01..2025-01, 2025-11..2025-12 |
| KXDIESELW | diesel price week | AAA | CUMUL | 7 | 197 | 186,121 | 2026-08..2026-09 | 2026-08..2026-09 |
| KXAAAGASMINTX | Texas lowest gas price yearly | AAA | CUMUL | 4 | 13 | 184,594 | 2024-12..2024-12, 2025-12..2025-12, 2026-09..2026-09 | 2024-12..2024-12, 2025-12..2025-12 |
| KXDIESELD | Daily Diesel Price | AAA | CUMUL | 40 | 894 | 181,740 | 2026-08..2026-09 | 2026-08..2026-09 |
| KXCORNW | Corn Weekly | Pyth, Trading Economics - Corn | CUMUL | 4 | 140 | 172,571 | 2026-04..2026-05 | 2026-05..2026-05 |
| KXLITHIUMMON | Lithium Monthly | Trading Economics - Lithium | CUMUL | 1 | 40 | 167,367 | 2026-04..2026-04 | none |
| KXNICKELMON | Nickel Monthly | Trading Economics - Nickel | CUMUL | 1 | 40 | 165,362 | 2026-04..2026-04 | 2026-04..2026-04 |
| KXOILRIGS | Oil rigs | The American Oil & Gas Reporter, the Ame | CUMUL | 2 | 23 | 144,303 | 2025-12..2025-12, 2026-09..2026-09 | 2025-12..2025-12 |
| KXNICKELW | Nickel Weekly | Trading Economics - Nickel | CUMUL | 4 | 170 | 140,332 | 2026-04..2026-05 | 2026-05..2026-05 |
| KXSUGARMON | Sugar Monthly | Trading Economics - Sugar | CUMUL | 1 | 34 | 134,021 | 2026-04..2026-04 | 2026-04..2026-04 |
| KXCOFFEEW | Weekly Coffee Price | Trading Economics - Coffee | CUMUL | 4 | 126 | 130,234 | 2026-04..2026-05 | 2026-04..2026-05 |
| KXLITHIUMW | Lithium Weekly | Trading Economics - Lithium | CUMUL | 4 | 190 | 129,341 | 2026-04..2026-05 | 2026-05..2026-05 |
| KXCORNMON | Corn Monthly | Trading Economics - Corn | CUMUL | 1 | 24 | 125,809 | 2026-04..2026-04 | 2026-04..2026-04 |
| KXSOLAR | Solar capcity installation | Solar Energy Industries Association | CUMUL | 2 | 10 | 124,756 | 2026-03..2026-03, 2026-09..2026-09 | 2026-03..2026-03 |
| KXSUGARW | Sugar Weekly | Trading Economics - Sugar | CUMUL | 4 | 116 | 123,844 | 2026-04..2026-05 | none |
| KXSOYBEANW | Soybean Weekly | Pyth, Trading Economics - Soybeans | CUMUL | 4 | 120 | 122,543 | 2026-04..2026-05 | none |
| KXWHEATMON | Wheat Monthly | Trading Economics - Wheat | CUMUL | 1 | 24 | 116,986 | 2026-04..2026-04 | 2026-04..2026-04 |
| KXWHEATW | Wheat Weekly | Pyth, Trading Economics - Wheat | CUMUL | 3 | 92 | 112,115 | 2026-04..2026-05 | 2026-05..2026-05 |
| KXLCATTLEMON | Live Cattle Monthly | Trading Economics - Live Cattle | CUMUL | 1 | 24 | 111,611 | 2026-04..2026-04 | 2026-04..2026-04 |
| KXWTIMINM | WTI oil monthly low | ICE | CUMUL | 3 | 31 | 107,739 | 2026-04..2026-06 | 2026-04..2026-06 |
| KXBTCVSGOLD | BTC vs Gold | CF Benchmarks | ICE, CF Benchmarks | Coi | CUMUL | 3 | 3 | 105,837 | 2025-11..2025-11, 2026-01..2026-01, 2026-09..2026-09 | 2025-11..2025-11, 2026-01..2026-01 |
| KXHOILW | Heating Oil Weekly | Trading Economics - Heating Oil | CUMUL | 4 | 110 | 105,710 | 2026-04..2026-05 | 2026-04..2026-05 |
| KXCOFFEEMON | Coffee Monthly | Trading Economics - Coffee | CUMUL | 1 | 20 | 104,835 | 2026-04..2026-04 | 2026-04..2026-04 |
| KXDIESELMON | Diesel Prices month | AAA | CUMUL | 2 | 52 | 104,750 | 2026-08..2026-09 | 2026-09..2026-09 |
| KXPOWERKWH | Average US electricity price this month | FRED | CUMUL | 4 | 31 | 104,237 | 2026-06..2026-09 | 2026-06..2026-09 |
| KXBARRELS | Oil barrels | U.S. Energy Information Administration | | CUMUL | 2 | 11 | 102,759 | 2025-12..2025-12, 2026-07..2026-07, 2026-09..2026-09 | 2025-12..2025-12, 2026-07..2026-07 |
| KXCOCOAW | Cocoa Directional Weekly | Trading Economics - Cocoa | CUMUL | 4 | 90 | 101,407 | 2026-04..2026-05 | 2026-04..2026-04 |
| KXSOYBEANMON | Soybean monthly | Trading Economics - Soybeans | CUMUL | 1 | 20 | 101,064 | 2026-04..2026-04 | 2026-04..2026-04 |
| KXAAAGASED | US gas price on Election Day | AAA | CUMUL | 1 | 11 | 98,555 | 2026-09..2026-09 | none |
| KXSPRLVL | SPR level on date | U.S. Energy Information Administration,  | CUMUL | 12 | 140 | 95,996 | 2026-04..2026-04, 2026-07..2026-09 | 2026-04..2026-04, 2026-07..2026-09 |
| KXAAAGASMINFL | Florida lowest gas price yearly | AAA | CUMUL | 2 | 7 | 95,651 | 2025-12..2025-12, 2026-09..2026-09 | 2025-12..2025-12 |
| KXLCATTLEW | Live Cattle Weekly | Trading Economics - Live Cattle | CUMUL | 4 | 90 | 94,966 | 2026-04..2026-05 | 2026-04..2026-05 |
| KXWTIDIRY | WTIDIRY | ICE | CUMUL | 1 | 11 | 92,478 | 2026-09..2026-09 | none |
| KXCOCOAMON | Cocoa Monthly | Trading Economics - Cocoa | CUMUL | 1 | 24 | 81,744 | 2026-04..2026-04 | 2026-04..2026-04 |
| KXAAAGASMAXFL | Florida highest gas price yearly | AAA | CUMUL | 2 | 19 | 78,912 | 2025-12..2025-12, 2026-02..2026-03, 2026-05..2026-05, 2026-09..2026-09 | 2025-12..2025-12, 2026-02..2026-03, 2026-05..2026-05 |
| KXAAAGASMIN | US lowest gas price yearly | AAA | CUMUL | 4 | 15 | 78,612 | 2023-11..2023-11, 2024-12..2024-12, 2026-07..2026-07, 2026-09..2026-09 | 2023-11..2023-11, 2024-12..2024-12, 2026-07..2026-07 |
| KXAAAGASDFL | Florida gas price | AAA | CUMUL | 17 | 376 | 78,378 | 2026-08..2026-09 | 2026-08..2026-09 |
| KXWTIWHEN | WTI When | ICE | CUMUL | 2 | 17 | 76,994 | 2026-07..2026-09 | 2026-07..2026-09 |
| KXAAAGASDTX | TX gas price | AAA | CUMUL | 19 | 373 | 68,928 | 2026-08..2026-09 | 2026-08..2026-09 |
| KXRHGOLD | RH gold | Robinhood | CUMUL | 8 | 47 | 68,079 | 2024-10..2024-10, 2025-02..2025-02, 2025-04..2025-05, 2025-07..2025-07, 2025-10..2025-10 | 2024-10..2024-10, 2025-02..2025-02, 2025-04..2025-05, 2025-07..2025-07 |
| KXJETFUEL | US Gulf Coast jet fuel price weekly | FRED | CUMUL | 12 | 131 | 67,812 | 2026-04..2026-07 | 2026-04..2026-04 |
| KXAAAGASDIL | Illinois gas price | AAA | CUMUL | 17 | 309 | 65,865 | 2026-08..2026-09 | 2026-08..2026-09 |
| KXHOILMON | Heating Oil Monthly | Trading Economics - Heating Oil | CUMUL | 1 | 20 | 60,852 | 2026-04..2026-04 | 2026-04..2026-04 |
| KXAAAGASDOH | Ohio gas price | AAA | CUMUL | 10 | 270 | 58,356 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXNGASMIN | Natural gas yearly low | Energy Information Administration | CUMUL | 3 | 14 | 55,685 | 2023-02..2023-02, 2025-12..2025-12, 2026-05..2026-05, 2026-09..2026-09 | 2023-02..2023-02, 2025-12..2025-12, 2026-05..2026-05 |
| KXNGAS | Natural gas price max and min monthly | Energy Information Administration | CUMUL | 4 | 16 | 55,612 | 2022-03..2022-03, 2022-06..2022-08 | 2022-03..2022-03, 2022-06..2022-07 |
| KXAAAGASDCA | California gas price | AAA | CUMUL | 17 | 309 | 55,150 | 2026-08..2026-09 | 2026-08..2026-09 |
| KXDXYVSGOLD | DXY vs. Gold | CNBC | Pyth | RANGE | 1 | 2 | 51,536 | 2026-09..2026-09 | none |
| KXAAAGASDNJ | New Jersey gas prices | AAA | CUMUL | 17 | 326 | 51,470 | 2026-08..2026-09 | 2026-08..2026-09 |
| KXGOLDVSSILVER | Gold vs. Silver | Pyth | RANGE | 1 | 2 | 48,115 | 2026-09..2026-09 | none |
| KXAAAGASDWA | Washington gas price | AAA | CUMUL | 10 | 174 | 44,876 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXAAAGASWNJ | New Jersey gas price this week | AAA | CUMUL | 3 | 74 | 42,393 | 2026-08..2026-09 | 2026-08..2026-09 |
| KXAAAGASDGA | Georgia gas price | AAA | CUMUL | 10 | 182 | 41,866 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXTXOIL | Texas crude oil production | U.S. Energy Information Administration | CUMUL | 1 | 4 | 40,952 | 2026-09..2026-09 | none |
| KXDIESELYE | Diesel prices at year end | AAA | CUMUL | 1 | 19 | 37,536 | 2026-09..2026-09 | none |
| KXAAAGASDNY | New York gas price | AAA | CUMUL | 17 | 289 | 37,456 | 2026-08..2026-09 | 2026-08..2026-09 |
| KXIRANCRUDE | Iran crude oil production in [month] | OPEC | CUMUL | 4 | 45 | 37,115 | 2026-07..2026-09 | 2026-07..2026-08 |
| KXAAAGASDNC | North Carolina gas price | AAA | CUMUL | 10 | 180 | 36,864 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXAAAGASDPA | Pennsylvania gas price | AAA | CUMUL | 10 | 210 | 36,682 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXILNUCLEAR | Illinois nuclear electricity generation | U.S. Energy Information Administration | CUMUL | 1 | 7 | 36,333 | 2026-09..2026-09 | none |
| KXDIESELELECT | Diesel prices on Election Day | AAA | CUMUL | 1 | 15 | 34,352 | 2026-09..2026-09 | none |
| KXPJMEMERGENCY | PJM capacity emergency days | PJM Interconnection - Emergency Procedur | CUMUL | 1 | 6 | 33,944 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXTXERCOTPEAK | Texas ERCOT peak electricity demand | Electric Reliability Council of Texas (E | CUMUL | 1 | 7 | 30,533 | 2026-09..2026-09 | none |
| KXWTIMAXM | WTI oil monthly high | ICE | CUMUL | 1 | 14 | 30,074 | 2026-06..2026-06 | 2026-06..2026-06 |
| KXAKPFD | Alaska Permanent Fund Dividend | State of Alaska | CUMUL | 1 | 5 | 28,663 | 2026-09..2026-09 | none |
| KXINXVSBTC | Will the S&P 500 outperform gold this ye | Google Finance | CF Benchmarks | RANGE | 1 | 2 | 27,725 | 2026-09..2026-09 | none |
| KXTXERCOTPEAKD | Texas ERCOT peak electricity demand | Electric Reliability Council of Texas (E | CUMUL | 14 | 175 | 25,714 | 2026-08..2026-09 | 2026-08..2026-09 |
| KXDIESELMAXY | Highest U.S. diesel price by year | AAA | CUMUL | 1 | 12 | 24,876 | 2026-09..2026-09 | none |
| KXTRUFGAS | Truflation US CPI Gasoline Price Index | Truflation US CPI Gasoline Price Index | CUMUL | 11 | 165 | 24,667 | 2026-06..2026-06, 2026-08..2026-08 | none |
| KXMEXCUBOIL | Mexico resumes oil exports to Cuba befor | AP | Bloomberg | Reuters | The New York  | CUMUL | 1 | 4 | 22,287 | 2026-07..2026-09 | 2026-07..2026-09 |
| KXOILW | Price of oil weekly | Energy Information Administration | CUMUL | 15 | 30 | 21,969 | 2022-03..2022-08 | 2022-03..2022-08 |
| KXDIESELMINY | Lowest U.S. diesel price by year | AAA | CUMUL | 1 | 12 | 21,770 | 2026-09..2026-09 | none |
| KXKSWHEAT | Kansas wheat production | USDA National Agricultural Statistics Se | CUMUL | 1 | 8 | 19,986 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXWTIVSBRENT | Will the WTI outperform Brent this year? | ICE | Pyth | RANGE | 1 | 2 | 19,840 | 2026-09..2026-09 | none |
| KXOPECCUTS | Oil production cuts | OPEC | OPEC+ | oil ministries of OPEC an | CUMUL | 1 | 1 | 19,734 | 2026-01..2026-01 | 2026-01..2026-01 |
| KXSPRMIN | SPRMIN | EIA | CUMUL | 2 | 2 | 19,534 | 2025-01..2025-01, 2026-01..2026-01 | 2025-01..2025-01, 2026-01..2026-01 |
| KXB65 | Beef 65 | USDA | CUMUL | 3 | 33 | 18,122 | 2026-08..2026-09 | 2026-08..2026-08 |
| KXINXVSGOLD | Will the S&P 500 outperform gold this ye | Google Finance | Pyth | RANGE | 1 | 2 | 16,911 | 2026-09..2026-09 | none |
| KXB85 | B85 | USDA | CUMUL | 3 | 33 | 14,890 | 2026-08..2026-09 | 2026-08..2026-08 |
| KXIAETHANOL | Iowa ethanol production | Iowa Renewable Fuels Association | CUMUL | 1 | 8 | 14,852 | 2026-09..2026-09 | none |
| KXMARCELLUSGAS | Marcellus natural gas production | U.S. Energy Information Administration | CUMUL | 1 | 6 | 14,791 | 2026-09..2026-09 | none |
| KXSDCORNYIELD | South Dakota corn yield | USDA National Agricultural Statistics Se | CUMUL | 1 | 8 | 14,668 | 2026-09..2026-09 | none |
| KXOPUS48OY | Opus 4.8 Output Token | Anthropic | CUMUL | 1 | 4 | 14,048 | 2026-09..2026-09 | none |
| KXWICORNYIELD | Wisconsin corn yield | USDA NASS | CUMUL | 1 | 9 | 13,688 | 2026-09..2026-09 | none |
| KXRIRESPOWER | Rhode Island residential electricity pri | U.S. Energy Information Administration | CUMUL | 1 | 7 | 13,636 | 2026-09..2026-09 | none |
| KXWYCOAL | Wyoming coal production | EIA Quarterly Coal Report | CUMUL | 1 | 8 | 12,914 | 2026-09..2026-09 | none |
| KXAAAGASMAXM | US highest gas price monthly | AAA | CUMUL | 1 | 9 | 12,908 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXWVCOAL | West Virginia coal production | EIA Quarterly Coal Report | CUMUL | 1 | 7 | 12,178 | 2026-09..2026-09 | none |
| KXGBT55OY | GPT 5.5 Input Token | OpenAI | CUMUL | 1 | 4 | 11,088 | 2026-09..2026-09 | none |
| KXGOLD | Price of gold | ICE | RANGE | 19 | 95 | 10,875 | 2022-09..2022-10 | 2022-10..2022-10 |
| KXAAAGASMINM | US lowest gas price monthly | AAA | CUMUL | 1 | 9 | 10,498 | 2026-09..2026-09 | none |
| KXMSCOTTON | Mississippi cotton production | USDA National Agricultural Statistics Se | CUMUL | 1 | 6 | 10,267 | 2026-09..2026-09 | none |
| KXNGASW | Natural gas price max and min weekly | Energy Information Administration | CUMUL | 5 | 13 | 9,744 | 2022-07..2022-08 | 2022-07..2022-08 |
| KXKYCOAL | Kentucky coal production | U.S. Energy Information Administration | CUMUL | 1 | 6 | 9,450 | 2026-09..2026-09 | none |
| KXNECORNYIELD | Nebraska corn yield | USDA National Agricultural Statistics Se | CUMUL | 1 | 5 | 8,671 | 2026-09..2026-09 | none |
| KXAAAGASDTN | Tennessee gas price | AAA | CUMUL | 2 | 44 | 7,848 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXINCORNYIELD | Indiana corn yield | USDA National Agricultural Statistics Se | CUMUL | 1 | 1 | 7,822 | 2026-09..2026-09 | none |
| KXSPRUSE | SPR use | the Department of Energy | the Office of | CUMUL | 1 | 3 | 7,770 | 2025-07..2025-09 | 2025-07..2025-09 |
| KXIACORN | Iowa corn production | USDA National Agricultural Statistics Se | CUMUL | 1 | 1 | 7,652 | 2026-09..2026-09 | none |
| KXVENEZCRUDE | Venezuela crude oil production in [month | OPEC | CUMUL | 1 | 8 | 7,607 | 2026-09..2026-09 | none |
| KXNMCOIL | New Mexico crude oil production | U.S. Energy Information Administration | CUMUL | 1 | 1 | 7,128 | 2026-09..2026-09 | none |
| KXGEMINI35OY | Gemini 3.5 Flash Output Token | Google Gemini Developer API pricing | CUMUL | 1 | 4 | 6,940 | 2026-09..2026-09 | none |
| KXAAAGASDVA | Virginia gas price | AAA | CUMUL | 2 | 44 | 5,387 | 2026-09..2026-09 | none |
| KXAAAGASDAZ | Arizona gas price | AAA | CUMUL | 2 | 34 | 5,339 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXPAGAS | Pennsylvania natural gas production | U.S. Energy Information Administration | CUMUL | 1 | 1 | 5,316 | 2026-09..2026-09 | none |
| KXAAAGASDMA | Massachusetts gas price | AAA | CUMUL | 2 | 34 | 4,896 | 2026-09..2026-09 | none |
| KXAAAGASDMI | Michigan gas price | AAA | CUMUL | 2 | 34 | 4,605 | 2026-09..2026-09 | 2026-09..2026-09 |
| KXNDKOIL | North Dakota crude oil production | U.S. Energy Information Administration | CUMUL | 1 | 1 | 3,782 | 2026-09..2026-09 | none |
| KXAKCRUDEOIL | Alaska crude oil production | U.S. Energy Information Administration | CUMUL | 1 | 1 | 3,741 | 2026-09..2026-09 | none |
| KXRUCRUDEX | Russia crude exports in [month] below x. | International Energy Agency | CUMUL | 1 | 1 | 3,711 | 2026-05..2026-05 | 2026-05..2026-05 |
| KXGEMINI35Y | Gemini 3.5 Flash | Google Gemini Developer API pricing | CUMUL | 1 | 4 | 3,620 | 2026-09..2026-09 | none |
| KXOPUS48Y | Opus 4.8 Input Token | Anthropic | CUMUL | 1 | 4 | 3,498 | 2026-09..2026-09 | none |
| KXGPT55Y | GPT 5.5 Input Token | OpenAI | CUMUL | 1 | 4 | 3,466 | 2026-09..2026-09 | none |
| KXEIACRUDEW | U.S. crude oil inventories | U.S. Energy Information Administration | CUMUL | 2 | 26 | 2,920 | 2026-09..2026-09 | none |
| KXLAOILGASEMP | Louisiana oil and gas extraction employm | Bureau of Labor Statistics | CUMUL | 1 | 1 | 2,737 | 2026-09..2026-09 | none |
| KXDOESPRTENDER | DOE Strategic Petroleum Reserve tenders | the U.S. Department of Energy, Office of | CUMUL | 1 | 3 | 2,607 | 2026-09..2026-09 | none |
| KXNECOF | Nebraska cattle on feed | USDA National Agricultural Statistics Se | CUMUL | 1 | 1 | 2,169 | 2026-09..2026-09 | none |
| KXVERARELEASE | Vera /rubin release | company | authorized retailers and distr | CUMUL | 1 | 6 | 1,956 | 2026-09..2026-09 | none |
| KXOKOIL | Oklahoma crude oil production | U.S. Energy Information Administration | CUMUL | 1 | 1 | 1,716 | 2026-09..2026-09 | none |
| KXBOEGOLD | BOE gold withdrawals | the BBC | The Guardian | The New York Ti | CUMUL | 1 | 1 | 1,677 | 2025-05..2025-05 | 2025-05..2025-05 |
| KXSDCATTLE | South Dakota cattle inventory | USDA NASS | CUMUL | 1 | 1 | 1,438 | 2026-09..2026-09 | none |
| KXAAAEVM | US EV charging price | AAA | CUMUL | 1 | 11 | 1,238 | 2026-08..2026-08 | none |
| KXMTCATTLE | Montana cattle inventory | USDA National Agricultural Statistics Se | CUMUL | 1 | 1 | 1,238 | 2026-09..2026-09 | none |
| KXKEYSTONEFID | Keystone XL final investment decision | South Bow Corporation | CUMUL | 1 | 4 | 897 | 2026-09..2026-09 | none |
| KXCHINAOILINV | China strategic oil inventories | U.S. Energy Information Administration | CUMUL | 1 | 5 | 775 | 2026-09..2026-09 | none |
| KXDIESELM | Diesel price this month | Energy Information Administration | CUMUL | 1 | 10 | 722 | 2022-11..2022-11 | 2022-11..2022-11 |
| KXDIESEL | Diesel price this week | Energy Information Administration | CUMUL | 7 | 26 | 701 | none | none |
| KXSTEELMON | Steel Monthly Price | Trading Economics - Steel Rebar Futures | RANGE | 2 | 80 | 40 | none | none |
| KXWHEAT | Average wheat price | United States Department of Agriculture | CUMUL | 1 | 1 | 31 | none | none |
| KXWTIEU | WTI oil up after election | ICE | CUMUL | 1 | 1 | 15 | none | none |
| KXIEAOIL | Will the IEA approve a strategic oil res | International Energy Agency (IEA) | CUMUL | 1 | 1 | 12 | none | none |
| KXWTIE | WTI oil election day | ICE | CUMUL | 1 | 15 | 10 | none | none |
| KXSTEELW | Steel Weekly Price | Trading Economics - Steel Rebar Futures | CUMUL | 2 | 80 | 0 | none | none |

`quoted window` = contiguous months in which at least 50% of that month's markets returned candles AND the month averaged at least 50 candles per market (someone was quoting). `tradeable window` = quoted months whose MEDIAN bracket had lifetime volume of at least 100 contracts (someone was trading). Candle density is not depth: the 2022-24 KXWTI era is quoted but mostly not tradeable.

## Series by settlement source

- **AAA**: KXAAAEVM, KXAAAGASD, KXAAAGASDAZ, KXAAAGASDCA, KXAAAGASDFL, KXAAAGASDGA, KXAAAGASDIL, KXAAAGASDMA, KXAAAGASDMI, KXAAAGASDNC, KXAAAGASDNJ, KXAAAGASDNY, KXAAAGASDOH, KXAAAGASDPA, KXAAAGASDTN, KXAAAGASDTX, KXAAAGASDVA, KXAAAGASDWA, KXAAAGASED, KXAAAGASM, KXAAAGASMAX, KXAAAGASMAXCA, KXAAAGASMAXFL, KXAAAGASMAXM, KXAAAGASMAXTX, KXAAAGASMIN, KXAAAGASMINCA, KXAAAGASMINFL, KXAAAGASMINM, KXAAAGASMINTX, KXAAAGASW, KXAAAGASWNJ, KXDIESELD, KXDIESELELECT, KXDIESELMAXY, KXDIESELMINY, KXDIESELMON, KXDIESELW, KXDIESELYE
- **U.S. Energy Information Administration**: KXAKCRUDEOIL, KXCHINAOILINV, KXEIACRUDEW, KXILNUCLEAR, KXKYCOAL, KXMARCELLUSGAS, KXNDKOIL, KXNMCOIL, KXOKOIL, KXPAGAS, KXRIRESPOWER, KXSPRLVL, KXTXOIL
- **Pyth**: KXBRENTD, KXBRENTMON, KXBRENTW, KXCOPPERD, KXCOPPERMON, KXCOPPERW, KXCORNW, KXGOLDVSSILVER, KXNATGASD, KXNATGASMON, KXNATGASW, KXSOYBEANW, KXWHEATW
- **ICE** (exchange-settled: CME/ICE option is a candidate hedge): KXGOLD, KXGOLDMON, KXGOLDW, KXWTI, KXWTIDIRY, KXWTIE, KXWTIEU, KXWTIMAX, KXWTIMAXM, KXWTIMIN, KXWTIMINM, KXWTIW, KXWTIWHEN
- **Energy Information Administration**: KXDIESEL, KXDIESELM, KXNGAS, KXNGASMAX, KXNGASMIN, KXNGASW, KXOIL, KXOILW
- **USDA National Agricultural Statistics Service**: KXIACORN, KXINCORNYIELD, KXKSWHEAT, KXMSCOTTON, KXMTCATTLE, KXNECOF, KXNECORNYIELD, KXSDCORNYIELD
- **Pyth - Gold**: KXGOLDD, KXGOLDDIRY, KXGOLDMON, KXGOLDW
- **Trading Economics - Brent crude oil**: KXBRENTD, KXBRENTMON, KXBRENTW
- **Trading Economics - Gold**: KXGOLDD, KXGOLDMON, KXGOLDW
- **FRED**: KXJETFUEL, KXPOWERKWH, KXUSGASCPI
- **Trading Economics - Natural Gas**: KXNATGASD, KXNATGASMON, KXNATGASW
- **Pyth - Silver**: KXSILVERD, KXSILVERMON, KXSILVERW
- **Trading Economics - Silver**: KXSILVERD, KXSILVERMON, KXSILVERW
- **USDA**: KXB65, KXB85
- **Trading Economics - Copper Futures | Trading Economics - Silver | Trading Economics - Brent crude oil | Trading Economics - Steel Rebar Futures**: KXBRENTD, KXGOLDD
- **Trading Economics - Cocoa**: KXCOCOAMON, KXCOCOAW
- **Trading Economics - Coffee**: KXCOFFEEMON, KXCOFFEEW
- **Trading Economics - Copper Futures**: KXCOPPERD, KXCOPPERMON
- **Trading Economics - Corn**: KXCORNMON, KXCORNW
- **OpenAI**: KXGBT55OY, KXGPT55Y
- **Google Gemini Developer API pricing**: KXGEMINI35OY, KXGEMINI35Y
- **Trading Economics - Heating Oil**: KXHOILMON, KXHOILW
- **OPEC**: KXIRANCRUDE, KXVENEZCRUDE
- **Trading Economics - Live Cattle**: KXLCATTLEMON, KXLCATTLEW
- **Trading Economics - Lithium**: KXLITHIUMMON, KXLITHIUMW
- **Trading Economics - Nickel**: KXNICKELMON, KXNICKELW
- **Anthropic**: KXOPUS48OY, KXOPUS48Y
- **USDA NASS**: KXSDCATTLE, KXWICORNYIELD
- **Trading Economics - Soybeans**: KXSOYBEANMON, KXSOYBEANW
- **Trading Economics**: KXSPRLVL, KXUSGASCPI
- **Trading Economics - Steel Rebar Futures**: KXSTEELMON, KXSTEELW
- **Trading Economics - Sugar**: KXSUGARMON, KXSUGARW
- **Electric Reliability Council of Texas (ERCOT)**: KXTXERCOTPEAK, KXTXERCOTPEAKD
- **Trading Economics - Wheat**: KXWHEATMON, KXWHEATW
- **EIA Quarterly Coal Report**: KXWVCOAL, KXWYCOAL
- **State of Alaska**: KXAKPFD
- **U.S. Energy Information Administration | The New York Times | the Associated Press | Bloomberg News | Reuters | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC | CBS | CNN | Fox News | MSNBC | NBC**: KXBARRELS
- **the Associated Press | Reuters | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC | CBS | CNN | Fox News | MSNBC | EIA**: KXBARRELS
- **the BBC | The Guardian | The New York Times | the Associated Press | Reuters | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC | CBS | CNN | Fox News | MSNBC**: KXBOEGOLD
- **Pyth - Brent**: KXBRENTD
- **CF Benchmarks | ICE** (exchange-settled: CME/ICE option is a candidate hedge): KXBTCVSGOLD
- **CF Benchmarks | CoinDesk | CoinGecko | Coinbase | Bloomberg Terminal | MarketWatch | Yahoo Finance | CNBC | The Wall Street Journal | Financial Times | Bloomberg News | Reuters**: KXBTCVSGOLD
- **Pyth - Copper**: KXCOPPERD
- **the U.S. Department of Energy, Office of Petroleum Reserves**: KXDOESPRTENDER
- **CNBC | Pyth**: KXDXYVSGOLD
- **Iowa Renewable Fuels Association**: KXIAETHANOL
- **International Energy Agency (IEA)**: KXIEAOIL
- **Google Finance | CF Benchmarks**: KXINXVSBTC
- **Google Finance | Pyth**: KXINXVSGOLD
- **South Bow Corporation**: KXKEYSTONEFID
- **Bureau of Labor Statistics**: KXLAOILGASEMP
- **AP | Bloomberg | Reuters | The New York Times | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC News | CBS News | CNN | Fox News | MSNBC | NBC News**: KXMEXCUBOIL
- **Pyth - NATGAS**: KXNATGASD
- **The American Oil & Gas Reporter**: KXOILRIGS
- **the American Oil & Gas reporter**: KXOILRIGS
- **OPEC | OPEC+ | oil ministries of OPEC and OPEC+ member countries | The New York Times | the Associated Press | Bloomberg News | Reuters | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC | CBS | CNN | Fox News | MSNBC | NBC | Financial Times | S&P Global Platts | Argus Media | Energy Intelligence | Oil Price Information Service**: KXOPECCUTS
- **PJM Interconnection - Emergency Procedures**: KXPJMEMERGENCY
- **Robinhood**: KXRHGOLD
- **International Energy Agency**: KXRUCRUDEX
- **Solar Energy Industries Association**: KXSOLAR
- **EIA**: KXSPRMIN
- **the Department of Energy | the Office of Petroleum Reserves | the White House | the President of the United States | The New York Times | the Associated Press | Bloomberg News | Reuters | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC | CBS | CNN | Fox News | MSNBC | NBC**: KXSPRUSE
- **Truflation US CPI Gasoline Price Index**: KXTRUFGAS
- **company | authorized retailers and distributors of company**: KXVERARELEASE
- **United States Department of Agriculture**: KXWHEAT
- **ICE | Pyth** (exchange-settled: CME/ICE option is a candidate hedge): KXWTIVSBRENT

## Databento shortlist

Series whose dominant settlement source is an exchange, with at least 2 TRADEABLE months (median bracket volume >= 100 contracts):

- **KXWTI** (ICE) tradeable 2022-09..2022-12, 2023-02..2023-03, 2026-03..2026-09; quoted 2022-09..2024-06, 2026-03..2026-09; 8,892,333 candles; front-month contracts seen: WBS 26U-ICE (700), WBS 26V-ICE (570), WBS 26Q-ICE (388)
- **KXWTIW** (ICE) tradeable 2022-09..2022-11, 2023-02..2023-02, 2024-04..2024-04, 2025-12..2026-09; quoted 2022-09..2024-08, 2025-11..2026-09; 2,311,548 candles; front-month contracts seen: WBS 26U-ICE (123), WBS 26V-ICE (108), WBS 26Q-ICE (60)
- **KXWTIMAX** (ICE) tradeable 2023-11..2023-12, 2024-12..2024-12, 2025-09..2025-09, 2025-12..2025-12, 2026-03..2026-04, 2026-07..2026-09; quoted 2023-11..2023-12, 2024-12..2024-12, 2025-09..2025-09, 2025-12..2025-12, 2026-03..2026-04, 2026-07..2026-09; 1,070,153 candles; front-month contracts seen: -
- **KXWTIMIN** (ICE) tradeable 2023-03..2023-03, 2023-12..2023-12, 2024-12..2024-12, 2025-11..2025-12, 2026-04..2026-04, 2026-06..2026-09; quoted 2023-03..2023-03, 2023-12..2023-12, 2024-09..2024-09, 2024-12..2024-12, 2025-11..2025-12, 2026-04..2026-04, 2026-06..2026-09; 436,785 candles; front-month contracts seen: -
- **KXWTIMINM** (ICE) tradeable 2026-04..2026-06; quoted 2026-04..2026-06; 107,739 candles; front-month contracts seen: -
- **KXBTCVSGOLD** (CF Benchmarks | ICE) tradeable 2025-11..2025-11, 2026-01..2026-01; quoted 2025-11..2025-11, 2026-01..2026-01, 2026-09..2026-09; 105,837 candles; front-month contracts seen: -
- **KXWTIWHEN** (ICE) tradeable 2026-07..2026-09; quoted 2026-07..2026-09; 76,994 candles; front-month contracts seen: -

Buy CME options history covering those windows (plus a month either side for the density fit warm-up). Everything else settles on an aggregated index or has no usable window yet.

## Tail depth on the shortlist (--tails)

Brackets are classified by their median mid over the tradeable months. Lifetime volume is contracts traded over the bracket's life (markets table); spread is the median close-to-close spread (candles). `< unit` = share of brackets with lifetime volume below the 500-contract standard unit. Spreads below 5c are unreliable: an empty book is served as a 0 ask.

### KXBTCVSGOLD - 2025-11..2025-11 - 2 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 1 | 446,595 | 446,595 | 446,595 | 0% | 1.0c | 1.0c |
| moderate tail | 5-20c | 0 | - | - | - | - | - | - |
| near the money | 20-80c | 0 | - | - | - | - | - | - |
| deep in the money | 80-100c | 1 | 333,080 | 333,080 | 333,080 | 0% | 1.0c | 1.0c |

### KXBTCVSGOLD - 2026-01..2026-01 - 2 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 1 | 446,595 | 446,595 | 446,595 | 0% | 1.0c | 1.0c |
| moderate tail | 5-20c | 0 | - | - | - | - | - | - |
| near the money | 20-80c | 1 | 268,944 | 268,944 | 268,944 | 0% | 3.0c | 3.0c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTI - 2022-09..2022-12 - 669 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 59 | 0 | 162 | 1,231 | 73% | 3.0c | 4.0c |
| moderate tail | 5-20c | 452 | 26 | 641 | 2,954 | 47% | 4.0c | 4.0c |
| near the money | 20-80c | 158 | 784 | 1,698 | 4,797 | 22% | 5.0c | 11.0c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTI - 2023-02..2023-03 - 354 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 28 | 0 | 0 | 315 | 93% | 3.0c | 3.2c |
| moderate tail | 5-20c | 183 | 58 | 513 | 1,888 | 49% | 3.0c | 4.0c |
| near the money | 20-80c | 143 | 0 | 69 | 2,209 | 59% | 87.0c | 99.0c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTI - 2026-03..2026-09 - 3096 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 340 | 819 | 3,066 | 13,005 | 19% | 1.0c | 2.0c |
| moderate tail | 5-20c | 515 | 5,608 | 12,089 | 61,300 | 2% | 2.0c | 3.0c |
| near the money | 20-80c | 1161 | 17,002 | 39,923 | 124,217 | 4% | 2.0c | 4.0c |
| deep in the money | 80-100c | 1080 | 940 | 3,162 | 37,109 | 15% | 2.0c | 3.0c |

### KXWTIMAX - 2023-11..2023-12 - 4 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 2 | 13,166 | 16,015 | 20,573 | 0% | 2.5c | 2.8c |
| moderate tail | 5-20c | 1 | 22,469 | 22,469 | 22,469 | 0% | 6.0c | 6.0c |
| near the money | 20-80c | 0 | - | - | - | - | - | - |
| deep in the money | 80-100c | 1 | 5,767 | 5,767 | 5,767 | 0% | 2.0c | 2.0c |

### KXWTIMAX - 2024-12..2024-12 - 9 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 0 | - | - | - | - | - | - |
| moderate tail | 5-20c | 2 | 3,059 | 3,898 | 5,241 | 0% | 14.0c | 15.5c |
| near the money | 20-80c | 7 | 5,349 | 11,878 | 553,917 | 0% | 96.0c | 96.8c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTIMAX - 2025-09..2025-09 - 5 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 0 | - | - | - | - | - | - |
| moderate tail | 5-20c | 2 | 13,838 | 15,798 | 18,934 | 0% | 14.5c | 16.8c |
| near the money | 20-80c | 2 | 360,693 | 682,734 | 1,197,999 | 0% | 85.2c | 88.6c |
| deep in the money | 80-100c | 1 | 1,637 | 1,637 | 1,637 | 0% | 33.0c | 33.0c |

### KXWTIMAX - 2025-12..2025-12 - 4 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 2 | 13,838 | 15,798 | 18,934 | 0% | 1.5c | 1.8c |
| moderate tail | 5-20c | 1 | 1,326,815 | 1,326,815 | 1,326,815 | 0% | 5.0c | 5.0c |
| near the money | 20-80c | 1 | 38,652 | 38,652 | 38,652 | 0% | 57.0c | 57.0c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTIMAX - 2026-03..2026-04 - 17 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 0 | - | - | - | - | - | - |
| moderate tail | 5-20c | 2 | 702,042 | 759,929 | 852,547 | 0% | 1.4c | 1.5c |
| near the money | 20-80c | 10 | 501,858 | 656,188 | 981,150 | 0% | 3.0c | 3.0c |
| deep in the money | 80-100c | 5 | 53,121 | 176,015 | 394,773 | 0% | 3.9c | 9.0c |

### KXWTIMAX - 2026-07..2026-09 - 114 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 0 | - | - | - | - | - | - |
| moderate tail | 5-20c | 13 | 4,404 | 16,080 | 839,724 | 0% | 14.0c | 17.0c |
| near the money | 20-80c | 94 | 156 | 1,212 | 18,311 | 43% | 51.2c | 65.4c |
| deep in the money | 80-100c | 7 | 1,125 | 2,772 | 5,911 | 14% | 5.5c | 11.0c |

### KXWTIMIN - 2023-03..2023-03 - 4 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 0 | - | - | - | - | - | - |
| moderate tail | 5-20c | 1 | 238 | 238 | 238 | 100% | 5.0c | 5.0c |
| near the money | 20-80c | 3 | 343 | 435 | 5,805 | 67% | 5.0c | 5.5c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTIMIN - 2023-12..2023-12 - 2 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 2 | 2,113 | 3,792 | 6,477 | 50% | 1.5c | 1.8c |
| moderate tail | 5-20c | 0 | - | - | - | - | - | - |
| near the money | 20-80c | 0 | - | - | - | - | - | - |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTIMIN - 2024-12..2024-12 - 6 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 0 | - | - | - | - | - | - |
| moderate tail | 5-20c | 1 | 2,905 | 2,905 | 2,905 | 0% | 30.0c | 30.0c |
| near the money | 20-80c | 5 | 1,193 | 1,918 | 16,457 | 20% | 93.0c | 95.0c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTIMIN - 2025-11..2025-12 - 4 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 0 | - | - | - | - | - | - |
| moderate tail | 5-20c | 1 | 7,693 | 7,693 | 7,693 | 0% | 8.0c | 8.0c |
| near the money | 20-80c | 2 | 5,816 | 11,310 | 20,102 | 50% | 27.0c | 36.5c |
| deep in the money | 80-100c | 1 | 1,193 | 1,193 | 1,193 | 0% | 8.0c | 8.0c |

### KXWTIMIN - 2026-04..2026-04 - 8 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 0 | - | - | - | - | - | - |
| moderate tail | 5-20c | 3 | 36,150 | 37,892 | 43,086 | 0% | 6.0c | 7.0c |
| near the money | 20-80c | 4 | 69,285 | 84,888 | 129,509 | 0% | 12.5c | 17.0c |
| deep in the money | 80-100c | 1 | 155,611 | 155,611 | 155,611 | 0% | 2.0c | 2.0c |

### KXWTIMIN - 2026-06..2026-09 - 71 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 9 | 2,623 | 4,890 | 8,503 | 0% | 1.0c | 2.0c |
| moderate tail | 5-20c | 25 | 384 | 1,685 | 9,637 | 32% | 4.0c | 10.0c |
| near the money | 20-80c | 36 | 670 | 1,967 | 51,497 | 22% | 8.0c | 13.2c |
| deep in the money | 80-100c | 1 | 14,296 | 14,296 | 14,296 | 0% | 4.0c | 4.0c |

### KXWTIMINM - 2026-04..2026-06 - 31 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 5 | 14,006 | 23,661 | 44,194 | 0% | 1.0c | 3.0c |
| moderate tail | 5-20c | 10 | 10,198 | 11,837 | 99,205 | 0% | 5.5c | 7.8c |
| near the money | 20-80c | 11 | 1,942 | 5,724 | 238,751 | 0% | 17.0c | 22.5c |
| deep in the money | 80-100c | 5 | 4,033 | 4,108 | 174,938 | 0% | 1.0c | 1.0c |

### KXWTIW - 2022-09..2022-11 - 135 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 35 | 0 | 15 | 530 | 89% | 3.0c | 4.0c |
| moderate tail | 5-20c | 96 | 40 | 500 | 3,212 | 50% | 4.0c | 4.0c |
| near the money | 20-80c | 4 | 2,716 | 4,806 | 8,082 | 0% | 5.0c | 5.0c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTIW - 2023-02..2023-02 - 75 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 5 | 0 | 0 | 33 | 100% | 2.0c | 3.0c |
| moderate tail | 5-20c | 53 | 100 | 661 | 3,616 | 45% | 3.0c | 4.0c |
| near the money | 20-80c | 17 | 0 | 0 | 140 | 100% | 99.0c | 99.0c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTIW - 2024-04..2024-04 - 75 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 30 | 0 | 302 | 3,613 | 63% | 3.0c | 4.0c |
| moderate tail | 5-20c | 36 | 0 | 12 | 5,300 | 69% | 4.0c | 10.2c |
| near the money | 20-80c | 9 | 12 | 511 | 6,348 | 44% | 4.0c | 56.0c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

### KXWTIW - 2025-12..2026-09 - 704 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 425 | 1,163 | 6,818 | 63,472 | 16% | 1.0c | 2.0c |
| moderate tail | 5-20c | 232 | 10,386 | 24,265 | 97,879 | 2% | 1.0c | 3.0c |
| near the money | 20-80c | 46 | 22,155 | 70,216 | 277,621 | 4% | 4.5c | 6.0c |
| deep in the money | 80-100c | 1 | 316,689 | 316,689 | 316,689 | 0% | 1.0c | 1.0c |

### KXWTIWHEN - 2026-07..2026-09 - 17 brackets

| band | mid | brackets | vol p25 | vol median | vol p90 | < unit | spread median | spread p75 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| deep tail | 0-5c | 0 | - | - | - | - | - | - |
| moderate tail | 5-20c | 8 | 2,841 | 3,781 | 8,992 | 0% | 3.5c | 4.0c |
| near the money | 20-80c | 9 | 2,063 | 2,471 | 6,077 | 0% | 11.0c | 20.0c |
| deep in the money | 80-100c | 0 | - | - | - | - | - | - |

## Month-by-month coverage

### KXWTI - WTI oil on day

cadence daily; ladder {"RANGE": 9222, "CUMUL": 3126}; settled 12183, with expiration_value 6900 (markets closing 2022-09 .. 2026-09); ticker formats {"old": 10355, "new": 1993}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2022-09 | 149 | 0 | 36,827 | 247 | 817 | 3,326 | 11% | yes | yes |
| 2022-10 | 170 | 0 | 36,566 | 215 | 1,030 | 4,298 | 9% | yes | yes |
| 2022-11 | 180 | 0 | 31,003 | 172 | 632 | 3,024 | 8% | yes | yes |
| 2022-12 | 170 | 0 | 33,167 | 195 | 566 | 3,184 | 17% | yes | yes |
| 2023-01 | 160 | 4 | 23,520 | 147 | 60 | 2,618 | 37% | yes |  |
| 2023-02 | 150 | 0 | 50,263 | 335 | 216 | 1,663 | 31% | yes | yes |
| 2023-03 | 194 | 0 | 82,713 | 426 | 371 | 2,448 | 28% | yes | yes |
| 2023-04 | 160 | 0 | 40,386 | 252 | 33 | 1,255 | 39% | yes |  |
| 2023-05 | 187 | 0 | 45,019 | 241 | 13 | 953 | 46% | yes |  |
| 2023-06 | 160 | 0 | 56,009 | 350 | 43 | 716 | 35% | yes |  |
| 2023-07 | 160 | 0 | 51,827 | 324 | 16 | 1,278 | 44% | yes |  |
| 2023-08 | 180 | 0 | 49,103 | 273 | 12 | 1,295 | 38% | yes |  |
| 2023-09 | 150 | 0 | 37,418 | 249 | 6 | 656 | 47% | yes |  |
| 2023-10 | 180 | 0 | 53,139 | 295 | 8 | 376 | 42% | yes |  |
| 2023-11 | 170 | 0 | 58,493 | 344 | 8 | 998 | 45% | yes |  |
| 2023-12 | 200 | 0 | 67,819 | 339 | 0 | 359 | 72% | yes |  |
| 2024-01 | 255 | 0 | 80,223 | 315 | 0 | 565 | 70% | yes |  |
| 2024-02 | 240 | 0 | 25,260 | 105 | 0 | 508 | 66% | yes |  |
| 2024-03 | 240 | 0 | 30,211 | 126 | 0 | 1,235 | 64% | yes |  |
| 2024-04 | 270 | 0 | 23,714 | 88 | 0 | 1,350 | 66% | yes |  |
| 2024-05 | 195 | 0 | 17,330 | 89 | 0 | 15 | 78% | yes |  |
| 2024-06 | 225 | 0 | 15,547 | 69 | 0 | 16 | 80% | yes |  |
| 2024-07 | 270 | 0 | 13,278 | 49 | 2 | 21 | 40% |  |  |
| 2024-08 | 255 | 0 | 8,026 | 31 | 2 | 2 | 35% |  |  |
| 2024-09 | 247 | 0 | 1,684 | 7 | 0 | 2 | 79% |  |  |
| 2024-10 | 315 | 101 | 2,013 | 6 | 0 | 0 | 91% |  |  |
| 2024-11 | 300 | 0 | 2,052 | 7 | 0 | 5 | 63% |  |  |
| 2024-12 | 315 | 87 | 2,711 | 9 | 0 | 0 | 93% |  |  |
| 2025-01 | 330 | 176 | 235 | 1 | 0 | 0 | 98% |  |  |
| 2025-02 | 285 | 270 | 32 | 0 | 0 | 0 | 100% |  |  |
| 2025-03 | 315 | 236 | 173 | 1 | 0 | 0 | 100% |  |  |
| 2025-04 | 330 | 315 | 25 | 0 | 0 | 0 | 100% |  |  |
| 2025-05 | 315 | 295 | 37 | 0 | 0 | 0 | 100% |  |  |
| 2025-06 | 300 | 266 | 557 | 2 | 0 | 0 | 98% |  |  |
| 2025-07 | 330 | 308 | 43 | 0 | 0 | 0 | 99% |  |  |
| 2025-08 | 315 | 310 | 8 | 0 | 0 | 0 | 100% |  |  |
| 2025-09 | 315 | 297 | 18 | 0 | 0 | 0 | 100% |  |  |
| 2025-10 | 330 | 323 | 15 | 0 | 0 | 0 | 100% |  |  |
| 2025-11 | 240 | 123 | 2,481 | 10 | 0 | 154 | 82% |  |  |
| 2026-03 | 362 | 0 | 460,816 | 1273 | 12,113 | 79,119 | 3% | yes | yes |
| 2026-04 | 501 | 0 | 894,373 | 1785 | 20,112 | 126,947 | 0% | yes | yes |
| 2026-05 | 330 | 0 | 782,588 | 2371 | 32,357 | 142,363 | 3% | yes | yes |
| 2026-06 | 320 | 0 | 579,837 | 1812 | 22,400 | 94,246 | 0% | yes | yes |
| 2026-07 | 628 | 0 | 982,734 | 1565 | 9,124 | 65,042 | 0% | yes | yes |
| 2026-08 | 640 | 0 | 946,098 | 1478 | 5,216 | 55,126 | 1% | yes | yes |
| 2026-09 | 315 | 0 | 3,266,942 | 10371 | 2,820 | 34,333 | 1% | yes | yes |

### KXNATGASD - Natural Gas Daily

cadence daily; ladder {"CUMUL": 7762}; settled 7692, with expiration_value 7592 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 7762}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 190 | 26 | 52,822 | 278 | 0 | 93 | 73% | yes |  |
| 2026-04 | 1380 | 0 | 677,293 | 491 | 3 | 696 | 47% | yes |  |
| 2026-05 | 1192 | 0 | 1,041,883 | 874 | 281 | 2,166 | 24% | yes | yes |
| 2026-06 | 1660 | 0 | 1,235,539 | 744 | 231 | 4,037 | 5% | yes | yes |
| 2026-07 | 1450 | 0 | 1,190,655 | 821 | 414 | 4,425 | 12% | yes | yes |
| 2026-08 | 1500 | 0 | 655,957 | 437 | 98 | 3,108 | 44% | yes |  |
| 2026-09 | 390 | 0 | 240,668 | 617 | 181 | 3,959 | 27% | yes | yes |

### KXSILVERD - Silver daily

cadence daily; ladder {"CUMUL": 3911}; settled 3871, with expiration_value 3871 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 3911}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 253 | 0 | 157,033 | 621 | 8 | 331 | 40% | yes |  |
| 2026-04 | 600 | 0 | 677,188 | 1129 | 250 | 1,495 | 8% | yes | yes |
| 2026-05 | 650 | 0 | 704,589 | 1084 | 525 | 3,542 | 6% | yes | yes |
| 2026-06 | 750 | 0 | 800,989 | 1068 | 1,204 | 9,275 | 5% | yes | yes |
| 2026-07 | 720 | 0 | 838,478 | 1165 | 882 | 8,814 | 7% | yes | yes |
| 2026-08 | 698 | 0 | 559,966 | 802 | 298 | 4,384 | 20% | yes | yes |
| 2026-09 | 240 | 0 | 156,444 | 652 | 95 | 1,606 | 7% | yes |  |

### KXGOLDD - Gold Daily

cadence daily; ladder {"CUMUL": 3873}; settled 3833, with expiration_value 3833 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 3873}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 253 | 0 | 223,024 | 882 | 40 | 1,328 | 34% | yes |  |
| 2026-04 | 620 | 0 | 642,117 | 1036 | 339 | 3,742 | 9% | yes | yes |
| 2026-05 | 610 | 0 | 629,090 | 1031 | 438 | 4,921 | 12% | yes | yes |
| 2026-06 | 730 | 0 | 754,274 | 1033 | 1,264 | 14,528 | 6% | yes | yes |
| 2026-07 | 720 | 0 | 817,304 | 1135 | 1,336 | 15,452 | 7% | yes | yes |
| 2026-08 | 700 | 0 | 638,970 | 913 | 1,000 | 14,189 | 17% | yes | yes |
| 2026-09 | 240 | 0 | 177,818 | 741 | 453 | 7,621 | 3% | yes | yes |

### KXBRENTD - Brent Oil Daily

cadence daily; ladder {"CUMUL": 2503}; settled 2483, with expiration_value 2463 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 2503}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 223 | 9 | 83,900 | 376 | 124 | 1,748 | 27% | yes | yes |
| 2026-04 | 480 | 0 | 441,243 | 919 | 1,083 | 9,329 | 5% | yes | yes |
| 2026-05 | 380 | 0 | 575,289 | 1514 | 6,748 | 27,682 | 2% | yes | yes |
| 2026-06 | 410 | 0 | 540,881 | 1319 | 4,976 | 27,965 | 1% | yes | yes |
| 2026-07 | 470 | 0 | 548,585 | 1167 | 3,605 | 18,518 | 3% | yes | yes |
| 2026-08 | 400 | 0 | 367,204 | 918 | 2,874 | 11,897 | 10% | yes | yes |
| 2026-09 | 140 | 0 | 103,745 | 741 | 2,138 | 12,695 | 1% | yes | yes |

### KXGOLDW - Gold Weekly price 

cadence weekly; ladder {"CUMUL": 1050}; settled 1050, with expiration_value 1010 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 1050}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 120 | 0 | 187,748 | 1565 | 222 | 2,406 | 11% | yes | yes |
| 2026-04 | 160 | 0 | 454,126 | 2838 | 264 | 3,548 | 4% | yes | yes |
| 2026-05 | 200 | 0 | 615,183 | 3076 | 494 | 4,982 | 10% | yes | yes |
| 2026-06 | 170 | 0 | 404,893 | 2382 | 1,166 | 8,799 | 6% | yes | yes |
| 2026-07 | 200 | 0 | 550,647 | 2753 | 801 | 7,451 | 10% | yes | yes |
| 2026-08 | 160 | 0 | 293,285 | 1833 | 1,391 | 13,572 | 14% | yes | yes |
| 2026-09 | 40 | 0 | 62,991 | 1575 | 561 | 12,757 | 5% | yes | yes |

### KXCOPPERD - Daily Copper

cadence daily; ladder {"CUMUL": 4378}; settled 4328, with expiration_value 4327 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 4378}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 240 | 0 | 81,870 | 341 | 0 | 64 | 74% | yes |  |
| 2026-04 | 650 | 0 | 409,224 | 630 | 11 | 709 | 35% | yes |  |
| 2026-05 | 650 | 0 | 445,392 | 685 | 6 | 1,134 | 34% | yes |  |
| 2026-06 | 870 | 0 | 563,501 | 648 | 119 | 3,406 | 21% | yes | yes |
| 2026-07 | 820 | 0 | 462,927 | 565 | 56 | 2,482 | 32% | yes |  |
| 2026-08 | 850 | 0 | 449,955 | 529 | 149 | 3,888 | 41% | yes | yes |
| 2026-09 | 298 | 0 | 145,162 | 487 | 536 | 7,611 | 28% | yes | yes |

### KXGOLDMON - Gold Monthly Price

cadence monthly; ladder {"CUMUL": 290, "RANGE": 40}; settled 290, with expiration_value 290 (markets closing 2026-02 .. 2026-08); ticker formats {"new": 330}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-02 | 40 | 0 | 67,755 | 1694 | 927 | 4,110 | 12% | yes | yes |
| 2026-03 | 40 | 0 | 55,531 | 1388 | 1,159 | 8,458 | 0% | yes | yes |
| 2026-04 | 40 | 0 | 575,501 | 14388 | 1,742 | 7,364 | 0% | yes | yes |
| 2026-05 | 40 | 0 | 404,919 | 10123 | 338 | 4,365 | 0% | yes | yes |
| 2026-06 | 40 | 0 | 363,952 | 9099 | 841 | 4,402 | 0% | yes | yes |
| 2026-07 | 40 | 0 | 488,784 | 12220 | 804 | 4,306 | 2% | yes | yes |
| 2026-08 | 50 | 0 | 325,305 | 6506 | 2,020 | 9,625 | 0% | yes | yes |
| 2026-09 | 40 | 0 | 47,017 | 1175 | 98 | 1,912 | 32% | yes |  |

### KXWTIW - WTI oil weekly range

cadence weekly; ladder {"RANGE": 3119}; settled 2462, with expiration_value 880 (markets closing 2022-09 .. 2026-09); ticker formats {"old": 2768, "new": 351}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2022-09 | 15 | 0 | 6,133 | 409 | 263 | 2,963 | 27% | yes | yes |
| 2022-10 | 60 | 0 | 45,545 | 759 | 488 | 3,280 | 18% | yes | yes |
| 2022-11 | 45 | 0 | 18,774 | 417 | 178 | 2,924 | 16% | yes | yes |
| 2022-12 | 75 | 0 | 41,325 | 551 | 50 | 2,462 | 8% | yes |  |
| 2023-01 | 60 | 0 | 21,128 | 352 | 9 | 1,608 | 37% | yes |  |
| 2023-02 | 60 | 0 | 98,871 | 1648 | 225 | 3,118 | 30% | yes | yes |
| 2023-03 | 75 | 0 | 161,151 | 2149 | 15 | 1,262 | 45% | yes |  |
| 2023-04 | 45 | 0 | 22,156 | 492 | 0 | 639 | 51% | yes |  |
| 2023-05 | 60 | 0 | 25,741 | 429 | 0 | 492 | 55% | yes |  |
| 2023-06 | 75 | 0 | 27,968 | 373 | 0 | 510 | 63% | yes |  |
| 2023-07 | 60 | 0 | 27,464 | 458 | 0 | 797 | 57% | yes |  |
| 2023-08 | 60 | 0 | 17,574 | 293 | 4 | 680 | 37% | yes |  |
| 2023-09 | 75 | 0 | 19,379 | 258 | 10 | 317 | 36% | yes |  |
| 2023-10 | 60 | 0 | 10,472 | 175 | 13 | 567 | 43% | yes |  |
| 2023-11 | 60 | 0 | 33,551 | 559 | 0 | 204 | 55% | yes |  |
| 2023-12 | 75 | 0 | 26,024 | 347 | 0 | 173 | 71% | yes |  |
| 2024-01 | 60 | 0 | 13,620 | 227 | 10 | 1,283 | 40% | yes |  |
| 2024-02 | 60 | 0 | 6,939 | 116 | 6 | 943 | 40% | yes |  |
| 2024-03 | 60 | 0 | 45,902 | 765 | 6 | 1,084 | 43% | yes |  |
| 2024-04 | 60 | 0 | 52,886 | 881 | 289 | 5,564 | 17% | yes | yes |
| 2024-05 | 60 | 0 | 20,927 | 349 | 0 | 26 | 63% | yes |  |
| 2024-06 | 60 | 0 | 11,544 | 192 | 0 | 41 | 78% | yes |  |
| 2024-07 | 60 | 0 | 10,934 | 182 | 1 | 5 | 42% | yes |  |
| 2024-08 | 75 | 0 | 11,340 | 151 | 2 | 6 | 16% | yes |  |
| 2024-09 | 60 | 0 | 2,378 | 40 | 0 | 11 | 57% |  |  |
| 2024-10 | 60 | 0 | 1,277 | 21 | 0 | 7 | 77% |  |  |
| 2024-11 | 75 | 0 | 2,240 | 30 | 0 | 5 | 61% |  |  |
| 2024-12 | 60 | 15 | 2,956 | 49 | 0 | 5 | 82% |  |  |
| 2025-01 | 75 | 18 | 113 | 2 | 0 | 0 | 100% |  |  |
| 2025-02 | 60 | 37 | 99 | 2 | 0 | 0 | 100% |  |  |
| 2025-03 | 60 | 11 | 175 | 3 | 0 | 0 | 100% |  |  |
| 2025-04 | 60 | 42 | 37 | 1 | 0 | 0 | 100% |  |  |
| 2025-05 | 75 | 68 | 11 | 0 | 0 | 0 | 100% |  |  |
| 2025-06 | 60 | 41 | 62 | 1 | 0 | 0 | 98% |  |  |
| 2025-07 | 45 | 26 | 172 | 4 | 0 | 0 | 91% |  |  |
| 2025-08 | 75 | 69 | 11 | 0 | 0 | 0 | 100% |  |  |
| 2025-09 | 60 | 42 | 42 | 1 | 0 | 0 | 97% |  |  |
| 2025-10 | 75 | 60 | 31 | 0 | 0 | 0 | 96% |  |  |
| 2025-11 | 60 | 11 | 3,588 | 60 | 30 | 8,155 | 47% | yes |  |
| 2025-12 | 45 | 0 | 11,430 | 254 | 183 | 3,485 | 20% | yes | yes |
| 2026-01 | 75 | 0 | 80,992 | 1080 | 7,606 | 52,273 | 0% | yes | yes |
| 2026-02 | 68 | 0 | 48,177 | 708 | 2,860 | 19,360 | 3% | yes | yes |
| 2026-03 | 60 | 0 | 168,367 | 2806 | 66,520 | 149,524 | 0% | yes | yes |
| 2026-04 | 60 | 0 | 201,710 | 3362 | 68,144 | 243,146 | 0% | yes | yes |
| 2026-05 | 75 | 0 | 315,089 | 4201 | 35,526 | 152,876 | 0% | yes | yes |
| 2026-06 | 60 | 0 | 114,061 | 1901 | 14,716 | 63,608 | 0% | yes | yes |
| 2026-07 | 99 | 0 | 281,962 | 2848 | 13,709 | 69,414 | 0% | yes | yes |
| 2026-08 | 108 | 0 | 205,282 | 1901 | 2,864 | 32,319 | 4% | yes | yes |
| 2026-09 | 54 | 0 | 93,938 | 1740 | 4,507 | 27,074 | 2% | yes | yes |

### KXSILVERMON - Silver Monthly Price

cadence monthly; ladder {"CUMUL": 240, "RANGE": 40}; settled 240, with expiration_value 240 (markets closing 2026-03 .. 2026-08); ticker formats {"new": 280}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 40 | 0 | 54,851 | 1371 | 558 | 4,246 | 0% | yes | yes |
| 2026-04 | 40 | 0 | 620,640 | 15516 | 1,221 | 4,057 | 0% | yes | yes |
| 2026-05 | 40 | 0 | 398,499 | 9962 | 662 | 2,634 | 0% | yes | yes |
| 2026-06 | 40 | 0 | 398,527 | 9963 | 1,231 | 3,863 | 0% | yes | yes |
| 2026-07 | 40 | 0 | 472,463 | 11812 | 1,300 | 4,354 | 0% | yes | yes |
| 2026-08 | 40 | 0 | 192,330 | 4808 | 2,125 | 6,539 | 0% | yes | yes |
| 2026-09 | 40 | 0 | 48,428 | 1211 | 88 | 1,866 | 32% | yes |  |

### KXSILVERW - Silver Weekly Price

cadence weekly; ladder {"CUMUL": 1050}; settled 1050, with expiration_value 1050 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 1050}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 120 | 0 | 162,386 | 1353 | 108 | 1,735 | 21% | yes | yes |
| 2026-04 | 170 | 0 | 373,521 | 2197 | 74 | 2,085 | 14% | yes |  |
| 2026-05 | 200 | 0 | 492,153 | 2461 | 200 | 2,939 | 14% | yes | yes |
| 2026-06 | 160 | 0 | 340,713 | 2129 | 1,029 | 8,613 | 16% | yes | yes |
| 2026-07 | 200 | 0 | 428,089 | 2140 | 360 | 4,576 | 24% | yes | yes |
| 2026-08 | 160 | 0 | 199,205 | 1245 | 37 | 7,093 | 39% | yes |  |
| 2026-09 | 40 | 0 | 41,161 | 1029 | 1 | 3,898 | 25% | yes |  |

### KXCOPPERW - Copper Weekly Price

cadence weekly; ladder {"CUMUL": 870}; settled 830, with expiration_value 830 (markets closing 2026-04 .. 2026-09); ticker formats {"new": 830, "none": 40}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 40 | 0 | 143,320 | 3583 | 235 | 1,619 | 12% | yes | yes |
| 2026-05 | 250 | 0 | 567,244 | 2269 | 10 | 1,347 | 46% | yes |  |
| 2026-06 | 180 | 0 | 346,487 | 1925 | 117 | 2,884 | 1% | yes | yes |
| 2026-07 | 200 | 0 | 489,495 | 2447 | 211 | 2,592 | 26% | yes | yes |
| 2026-08 | 160 | 0 | 274,199 | 1714 | 166 | 3,764 | 36% | yes | yes |
| 2026-09 | 40 | 0 | 64,111 | 1603 | 1,641 | 14,627 | 20% | yes | yes |

### KXAAAGASM - US gas price

cadence monthly; ladder {"CUMUL": 470}; settled 425, with expiration_value 423 (markets closing 2023-12 .. 2026-08); ticker formats {"old": 470}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-12 | 1 | 0 | 146 | 146 | 4,730 | 4,730 | 0% | yes | yes |
| 2024-01 | 1 | 0 | 34 | 34 | 8 | 8 | 0% |  |  |
| 2024-02 | 1 | 0 | 85 | 85 | 1,919 | 1,919 | 0% | yes | yes |
| 2024-03 | 1 | 0 | 43 | 43 | 1,722 | 1,722 | 0% |  |  |
| 2024-04 | 1 | 0 | 156 | 156 | 3,937 | 3,937 | 0% | yes | yes |
| 2024-05 | 7 | 0 | 918 | 131 | 2,222 | 9,823 | 14% | yes | yes |
| 2024-06 | 8 | 0 | 1,317 | 165 | 7,274 | 21,539 | 12% | yes | yes |
| 2024-07 | 10 | 0 | 1,382 | 138 | 1,118 | 7,342 | 0% | yes | yes |
| 2024-08 | 10 | 0 | 1,481 | 148 | 3,042 | 17,295 | 0% | yes | yes |
| 2024-09 | 10 | 0 | 1,212 | 121 | 2,570 | 9,513 | 0% | yes | yes |
| 2024-10 | 8 | 0 | 2,541 | 318 | 1,842 | 11,630 | 0% | yes | yes |
| 2024-11 | 5 | 0 | 14,219 | 2844 | 25,582 | 55,319 | 0% | yes | yes |
| 2024-12 | 5 | 0 | 1,174 | 235 | 10,863 | 45,996 | 0% | yes | yes |
| 2025-01 | 6 | 0 | 2,799 | 466 | 4,426 | 12,311 | 0% | yes | yes |
| 2025-02 | 4 | 0 | 473 | 118 | 93 | 849 | 25% | yes |  |
| 2025-03 | 5 | 0 | 24,974 | 4995 | 14,210 | 17,295 | 0% | yes | yes |
| 2025-04 | 7 | 0 | 34,545 | 4935 | 635,437 | 1,276,391 | 0% | yes | yes |
| 2025-05 | 7 | 0 | 100,939 | 14420 | 1,135,738 | 1,902,388 | 0% | yes | yes |
| 2025-06 | 11 | 0 | 117,464 | 10679 | 989,781 | 2,144,525 | 0% | yes | yes |
| 2025-07 | 9 | 0 | 73,902 | 8211 | 216,571 | 1,378,166 | 0% | yes | yes |
| 2025-08 | 11 | 0 | 51,238 | 4658 | 31,924 | 959,008 | 0% | yes | yes |
| 2025-09 | 10 | 0 | 36,597 | 3660 | 60,919 | 616,810 | 0% | yes | yes |
| 2025-10 | 11 | 0 | 37,179 | 3380 | 28,146 | 846,602 | 0% | yes | yes |
| 2025-11 | 10 | 0 | 42,379 | 4238 | 28,658 | 447,872 | 0% | yes | yes |
| 2025-12 | 10 | 0 | 63,963 | 6396 | 67,128 | 399,170 | 0% | yes | yes |
| 2026-01 | 11 | 0 | 75,382 | 6853 | 101,530 | 315,921 | 0% | yes | yes |
| 2026-02 | 16 | 0 | 49,005 | 3063 | 89,004 | 188,682 | 0% | yes | yes |
| 2026-03 | 34 | 0 | 165,014 | 4853 | 112,220 | 411,979 | 0% | yes | yes |
| 2026-04 | 41 | 0 | 112,202 | 2737 | 47,056 | 272,419 | 0% | yes | yes |
| 2026-05 | 41 | 0 | 95,087 | 2319 | 55,871 | 352,323 | 0% | yes | yes |
| 2026-06 | 33 | 0 | 78,775 | 2387 | 13,798 | 58,677 | 0% | yes | yes |
| 2026-07 | 36 | 0 | 126,407 | 3511 | 33,171 | 88,008 | 0% | yes | yes |
| 2026-08 | 44 | 0 | 208,447 | 4737 | 9,735 | 77,963 | 0% | yes | yes |
| 2026-09 | 33 | 7 | 23,538 | 713 | 633 | 10,112 | 0% | yes | yes |
| 2026-10 | 7 | 7 | 0 | 0 | 0 | 0 | 100% |  |  |
| 2026-11 | 5 | 5 | 0 | 0 | 0 | 0 | 100% |  |  |

### KXBRENTMON - Brent Monthly

cadence monthly; ladder {"CUMUL": 150}; settled 110, with expiration_value 90 (markets closing 2026-04 .. 2026-08); ticker formats {"new": 150}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 20 | 0 | 225,931 | 11297 | 19,079 | 42,299 | 0% | yes | yes |
| 2026-05 | 20 | 0 | 438,479 | 21924 | 23,165 | 41,953 | 0% | yes | yes |
| 2026-06 | 20 | 0 | 208,123 | 10406 | 36,209 | 166,907 | 0% | yes | yes |
| 2026-07 | 30 | 0 | 256,210 | 8540 | 6,500 | 43,184 | 0% | yes | yes |
| 2026-08 | 20 | 0 | 152,097 | 7605 | 10,717 | 19,247 | 0% | yes | yes |
| 2026-09 | 40 | 0 | 36,092 | 902 | 475 | 6,965 | 32% | yes | yes |

### KXBRENTW - Brent Oil

cadence weekly; ladder {"CUMUL": 520}; settled 520, with expiration_value 520 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 520}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 20 | 0 | 26,094 | 1305 | 166 | 1,315 | 20% | yes | yes |
| 2026-04 | 100 | 0 | 223,699 | 2237 | 2,286 | 20,580 | 7% | yes | yes |
| 2026-05 | 110 | 0 | 458,086 | 4164 | 3,952 | 45,320 | 0% | yes | yes |
| 2026-06 | 80 | 0 | 160,058 | 2001 | 6,964 | 44,860 | 2% | yes | yes |
| 2026-07 | 110 | 0 | 286,688 | 2606 | 3,066 | 46,862 | 8% | yes | yes |
| 2026-08 | 80 | 0 | 133,935 | 1674 | 3,374 | 25,732 | 11% | yes | yes |
| 2026-09 | 20 | 0 | 27,734 | 1387 | 2,001 | 19,305 | 0% | yes | yes |

### KXAAAGASW - US gas price up

cadence weekly; ladder {"CUMUL": 927}; settled 885, with expiration_value 885 (markets closing 2023-10 .. 2026-09); ticker formats {"old": 897, "none": 30}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-10 | 16 | 0 | 195 | 12 | 42 | 574 | 38% |  |  |
| 2023-11 | 5 | 0 | 36 | 7 | 105 | 169 | 40% |  |  |
| 2023-12 | 4 | 0 | 132 | 33 | 153 | 963 | 0% |  |  |
| 2024-01 | 2 | 0 | 43 | 22 | 0 | 0 | 100% |  |  |
| 2024-05 | 3 | 0 | 129 | 43 | 1,419 | 2,925 | 0% |  |  |
| 2024-06 | 4 | 0 | 127 | 32 | 1,849 | 2,758 | 0% |  |  |
| 2024-07 | 5 | 0 | 535 | 107 | 3,890 | 11,176 | 0% | yes | yes |
| 2024-08 | 4 | 0 | 340 | 85 | 6,376 | 10,364 | 0% | yes | yes |
| 2024-09 | 5 | 0 | 186 | 37 | 1,484 | 1,623 | 0% |  |  |
| 2024-10 | 4 | 0 | 684 | 171 | 1,056 | 22,408 | 0% | yes | yes |
| 2024-11 | 4 | 0 | 5,463 | 1366 | 93,113 | 142,031 | 0% | yes | yes |
| 2024-12 | 5 | 0 | 3,319 | 664 | 56,791 | 66,254 | 0% | yes | yes |
| 2025-01 | 4 | 0 | 1,418 | 354 | 8,587 | 17,045 | 0% | yes | yes |
| 2025-02 | 4 | 0 | 2,680 | 670 | 10,912 | 31,302 | 0% | yes | yes |
| 2025-03 | 5 | 0 | 4,728 | 946 | 6,137 | 9,838 | 0% | yes | yes |
| 2025-04 | 4 | 0 | 2,143 | 536 | 2,724 | 12,707 | 0% | yes | yes |
| 2025-05 | 4 | 0 | 5,454 | 1364 | 1,629 | 7,254 | 0% | yes | yes |
| 2025-06 | 5 | 0 | 5,379 | 1076 | 20,873 | 22,524 | 0% | yes | yes |
| 2025-07 | 4 | 0 | 7,802 | 1950 | 33,958 | 41,358 | 0% | yes | yes |
| 2025-08 | 4 | 0 | 6,021 | 1505 | 53,926 | 183,076 | 0% | yes | yes |
| 2025-09 | 5 | 0 | 6,989 | 1398 | 65,979 | 117,076 | 0% | yes | yes |
| 2025-10 | 4 | 0 | 3,986 | 996 | 45,810 | 63,400 | 0% | yes | yes |
| 2025-11 | 4 | 0 | 5,168 | 1292 | 42,696 | 58,904 | 0% | yes | yes |
| 2025-12 | 7 | 0 | 8,177 | 1168 | 17,785 | 223,436 | 0% | yes | yes |
| 2026-01 | 8 | 0 | 25,636 | 3204 | 389,660 | 1,386,560 | 0% | yes | yes |
| 2026-02 | 15 | 0 | 37,632 | 2509 | 210,449 | 709,474 | 0% | yes | yes |
| 2026-03 | 156 | 21 | 172,454 | 1105 | 12,893 | 172,440 | 13% | yes | yes |
| 2026-04 | 89 | 0 | 131,597 | 1479 | 52,879 | 289,671 | 0% | yes | yes |
| 2026-05 | 96 | 0 | 136,580 | 1423 | 26,805 | 157,688 | 0% | yes | yes |
| 2026-06 | 146 | 0 | 193,080 | 1322 | 15,360 | 59,554 | 0% | yes | yes |
| 2026-07 | 98 | 0 | 197,521 | 2016 | 16,233 | 79,725 | 0% | yes | yes |
| 2026-08 | 148 | 0 | 157,998 | 1068 | 8,550 | 53,212 | 0% | yes | yes |
| 2026-09 | 56 | 0 | 47,791 | 853 | 11,272 | 51,714 | 0% | yes | yes |

### KXCOPPERMON - Copper Monthly Price

cadence monthly; ladder {"CUMUL": 250, "RANGE": 40}; settled 240, with expiration_value 240 (markets closing 2026-03 .. 2026-08); ticker formats {"new": 290}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 40 | 0 | 24,226 | 606 | 83 | 2,801 | 20% | yes |  |
| 2026-04 | 40 | 0 | 116,671 | 2917 | 210 | 968 | 0% | yes | yes |
| 2026-05 | 40 | 0 | 249,301 | 6233 | 78 | 728 | 5% | yes |  |
| 2026-06 | 40 | 0 | 294,441 | 7361 | 473 | 3,091 | 22% | yes | yes |
| 2026-07 | 40 | 0 | 222,721 | 5568 | 104 | 1,823 | 32% | yes | yes |
| 2026-08 | 40 | 0 | 175,367 | 4384 | 334 | 4,229 | 10% | yes | yes |
| 2026-09 | 50 | 0 | 51,243 | 1025 | 1,201 | 7,161 | 0% | yes | yes |

### KXWTIMAX - WTI oil high

cadence longer; ladder {"CUMUL": 135}; settled 96, with expiration_value 96 (markets closing 2023-11 .. 2026-09); ticker formats {"old": 135}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-11 | 1 | 0 | 19,946 | 19946 | 5,767 | 5,767 | 0% | yes | yes |
| 2023-12 | 3 | 0 | 62,969 | 20990 | 21,713 | 22,318 | 0% | yes | yes |
| 2024-12 | 4 | 0 | 43,222 | 10806 | 3,898 | 8,016 | 0% | yes | yes |
| 2025-09 | 1 | 0 | 456 | 456 | 1,637 | 1,637 | 0% | yes | yes |
| 2025-12 | 4 | 0 | 38,390 | 9598 | 29,185 | 940,366 | 0% | yes | yes |
| 2026-03 | 5 | 0 | 15,246 | 3049 | 53,121 | 349,800 | 0% | yes | yes |
| 2026-04 | 2 | 0 | 18,703 | 9352 | 217,635 | 274,285 | 0% | yes | yes |
| 2026-07 | 45 | 1 | 91,383 | 2031 | 3,136 | 18,995 | 4% | yes | yes |
| 2026-08 | 20 | 0 | 103,761 | 5188 | 901 | 5,018 | 0% | yes | yes |
| 2026-09 | 50 | 0 | 676,077 | 13522 | 482 | 6,094 | 22% | yes | yes |

### KXNATGASW - Natural Gas Weekly

cadence weekly; ladder {"CUMUL": 949}; settled 949, with expiration_value 949 (markets closing 2026-04 .. 2026-09); ticker formats {"new": 949}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 170 | 0 | 209,175 | 1230 | 3 | 1,142 | 36% | yes |  |
| 2026-05 | 200 | 0 | 375,939 | 1880 | 1 | 1,235 | 28% | yes |  |
| 2026-06 | 160 | 0 | 132,798 | 830 | 154 | 2,514 | 23% | yes | yes |
| 2026-07 | 200 | 0 | 208,201 | 1041 | 200 | 3,441 | 32% | yes | yes |
| 2026-08 | 160 | 0 | 77,867 | 487 | 2 | 2,533 | 48% | yes |  |
| 2026-09 | 59 | 0 | 33,278 | 564 | 3,121 | 12,506 | 20% | yes | yes |

### KXNATGASMON - Natural Gas Monthly

cadence monthly; ladder {"CUMUL": 240}; settled 200, with expiration_value 200 (markets closing 2026-04 .. 2026-08); ticker formats {"new": 240}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 40 | 0 | 40,576 | 1014 | 254 | 736 | 5% | yes | yes |
| 2026-05 | 40 | 0 | 162,985 | 4075 | 10 | 2,307 | 22% | yes |  |
| 2026-06 | 40 | 0 | 208,709 | 5218 | 76 | 1,620 | 0% | yes |  |
| 2026-07 | 40 | 0 | 241,074 | 6027 | 441 | 2,204 | 2% | yes | yes |
| 2026-08 | 40 | 0 | 66,564 | 1664 | 51 | 982 | 38% | yes |  |
| 2026-09 | 40 | 0 | 21,087 | 527 | 1 | 436 | 35% | yes |  |

### KXAAAGASD - US gas price up

cadence daily; ladder {"CUMUL": 3057}; settled 3030, with expiration_value 3030 (markets closing 2023-09 .. 2026-09); ticker formats {"old": 3057}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-09 | 11 | 0 | 122 | 11 | 26 | 170 | 18% |  |  |
| 2023-10 | 12 | 1 | 66 | 6 | 52 | 147 | 42% |  |  |
| 2024-05 | 2 | 1 | 4 | 2 | 0 | 0 | 100% |  |  |
| 2026-03 | 60 | 0 | 9,538 | 159 | 2,814 | 13,907 | 0% | yes | yes |
| 2026-04 | 583 | 0 | 57,867 | 99 | 1,036 | 10,200 | 0% | yes | yes |
| 2026-05 | 584 | 0 | 173,543 | 297 | 2,248 | 19,609 | 3% | yes | yes |
| 2026-06 | 469 | 0 | 101,693 | 217 | 4,027 | 23,546 | 1% | yes | yes |
| 2026-07 | 587 | 0 | 164,741 | 281 | 4,372 | 24,432 | 1% | yes | yes |
| 2026-08 | 530 | 0 | 122,773 | 232 | 4,324 | 33,243 | 0% | yes | yes |
| 2026-09 | 219 | 0 | 52,467 | 240 | 6,654 | 35,033 | 0% | yes | yes |

### KXWTIMIN - WTI oil low

cadence longer; ladder {"CUMUL": 83}; settled 51, with expiration_value 51 (markets closing 2023-03 .. 2026-08); ticker formats {"old": 83}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-03 | 1 | 0 | 4,006 | 4006 | 251 | 251 | 0% | yes | yes |
| 2023-12 | 3 | 0 | 53,068 | 17689 | 435 | 5,805 | 0% | yes | yes |
| 2024-09 | 1 | 0 | 5,170 | 5170 | 86 | 86 | 0% | yes |  |
| 2024-12 | 2 | 0 | 6,078 | 3039 | 2,412 | 2,806 | 0% | yes | yes |
| 2025-11 | 2 | 0 | 1,466 | 733 | 757 | 1,106 | 0% | yes | yes |
| 2025-12 | 2 | 0 | 20,283 | 10142 | 14,996 | 20,839 | 0% | yes | yes |
| 2026-04 | 1 | 0 | 2,836 | 2836 | 155,611 | 155,611 | 0% | yes | yes |
| 2026-06 | 3 | 0 | 75,007 | 25002 | 96,933 | 134,163 | 0% | yes | yes |
| 2026-07 | 16 | 0 | 27,450 | 1716 | 4,805 | 9,364 | 0% | yes | yes |
| 2026-08 | 20 | 0 | 40,268 | 2013 | 688 | 2,774 | 0% | yes | yes |
| 2026-09 | 32 | 0 | 201,153 | 6286 | 1,350 | 3,328 | 0% | yes | yes |

### KXUSGASCPI - US gasoline CPI in [month]

cadence monthly; ladder {"CUMUL": 129}; settled 104, with expiration_value 104 (markets closing 2026-04 .. 2026-08); ticker formats {"old": 129}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 17 | 0 | 8,457 | 497 | 1,820 | 6,076 | 0% | yes | yes |
| 2026-05 | 15 | 0 | 3,237 | 216 | 150 | 2,009 | 0% | yes | yes |
| 2026-06 | 22 | 0 | 83,129 | 3779 | 6,116 | 38,141 | 0% | yes | yes |
| 2026-07 | 23 | 0 | 79,768 | 3468 | 1,147 | 4,093 | 0% | yes | yes |
| 2026-08 | 27 | 0 | 100,517 | 3723 | 2,787 | 15,555 | 0% | yes | yes |
| 2026-09 | 25 | 0 | 32,284 | 1291 | 545 | 6,520 | 12% | yes | yes |

### KXAAAGASMAXCA - California highest gas price yearly

cadence longer; ladder {"CUMUL": 33}; settled 23, with expiration_value 23 (markets closing 2023-10 .. 2026-04); ticker formats {"old": 33}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-10 | 1 | 0 | 36 | 36 | 1,811 | 1,811 | 0% |  |  |
| 2023-12 | 1 | 0 | 374 | 374 | 350 | 350 | 0% | yes | yes |
| 2024-07 | 1 | 0 | 109 | 109 | 1,303 | 1,303 | 0% | yes | yes |
| 2024-12 | 1 | 0 | 369 | 369 | 1,112 | 1,112 | 0% | yes | yes |
| 2025-12 | 1 | 0 | 35,087 | 35087 | 105,656 | 105,656 | 0% | yes | yes |
| 2026-02 | 4 | 0 | 7,396 | 1849 | 162 | 14,382 | 0% | yes | yes |
| 2026-03 | 12 | 0 | 38,767 | 3231 | 341 | 2,958 | 0% | yes | yes |
| 2026-04 | 2 | 0 | 6,997 | 3498 | 2,806 | 4,374 | 0% | yes | yes |
| 2026-09 | 10 | 0 | 183,271 | 18327 | - | - | - | yes |  |

### KXGOLDDIRY - GOLDDIRY

cadence longer; ladder {"CUMUL": 13}; settled 0, with expiration_value 0; ticker formats {"new": 13}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 13 | 0 | 230,859 | 17758 | - | - | - | yes |  |

### KXAAAGASMINCA - California lowest gas price yearly

cadence longer; ladder {"CUMUL": 12}; settled 8, with expiration_value 8 (markets closing 2023-11 .. 2026-01); ticker formats {"old": 12}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-11 | 1 | 0 | 81 | 81 | 3,105 | 3,105 | 0% | yes | yes |
| 2024-11 | 1 | 0 | 181 | 181 | 129 | 129 | 0% | yes | yes |
| 2024-12 | 2 | 0 | 2,325 | 1162 | 5,110 | 6,953 | 0% | yes | yes |
| 2025-07 | 1 | 0 | 3,962 | 3962 | 5,346 | 5,346 | 0% | yes | yes |
| 2025-12 | 2 | 0 | 101,422 | 50711 | 135,610 | 148,040 | 0% | yes | yes |
| 2026-01 | 1 | 0 | 567 | 567 | 1,523 | 1,523 | 0% | yes | yes |
| 2026-09 | 4 | 0 | 118,033 | 29508 | - | - | - | yes |  |

### KXOIL - Price of oil monthly

cadence monthly; ladder {"CUMUL": 28}; settled 28, with expiration_value 28 (markets closing 2022-03 .. 2022-08); ticker formats {"old": 28}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2022-03 | 1 | 0 | 210 | 210 | 19,689 | 19,689 | 0% | yes | yes |
| 2022-04 | 9 | 0 | 21,787 | 2421 | 6,058 | 51,379 | 11% | yes | yes |
| 2022-05 | 4 | 0 | 3,158 | 790 | 1,952 | 3,783 | 25% | yes | yes |
| 2022-06 | 5 | 0 | 120,466 | 24093 | 13,871 | 32,160 | 0% | yes | yes |
| 2022-07 | 4 | 0 | 38,270 | 9568 | 18,428 | 59,088 | 0% | yes | yes |
| 2022-08 | 5 | 0 | 41,871 | 8374 | 4,914 | 27,991 | 0% | yes | yes |

### KXAAAGASMAXTX - Texas highest gas price yearly

cadence longer; ladder {"CUMUL": 27}; settled 17, with expiration_value 17 (markets closing 2023-12 .. 2026-05); ticker formats {"old": 27}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-12 | 2 | 0 | 13 | 6 | 2 | 4 | 50% |  |  |
| 2024-12 | 2 | 0 | 181 | 90 | 286 | 491 | 0% | yes | yes |
| 2025-12 | 2 | 0 | 80,647 | 40324 | 79,920 | 96,029 | 0% | yes | yes |
| 2026-02 | 2 | 0 | 1,273 | 636 | 620 | 1,081 | 0% | yes | yes |
| 2026-03 | 7 | 0 | 18,956 | 2708 | 517 | 46,948 | 14% | yes | yes |
| 2026-04 | 1 | 0 | 2,531 | 2531 | 6,112 | 6,112 | 0% | yes | yes |
| 2026-05 | 1 | 0 | 4,862 | 4862 | 6,316 | 6,316 | 0% | yes | yes |
| 2026-09 | 10 | 0 | 115,114 | 11511 | - | - | - | yes |  |

### KXAAAGASMAX - US highest gas price yearly

cadence longer; ladder {"CUMUL": 20}; settled 7, with expiration_value 6 (markets closing 2023-12 .. 2026-05); ticker formats {"old": 20}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-12 | 1 | 0 | 7 | 7 | 140 | 140 | 0% |  |  |
| 2024-12 | 2 | 0 | 4,146 | 2073 | 6,805 | 7,342 | 0% | yes | yes |
| 2025-12 | 1 | 1 | 0 | 0 | 0 | 0 | 100% |  |  |
| 2026-03 | 1 | 0 | 322 | 322 | 322 | 322 | 0% | yes | yes |
| 2026-04 | 1 | 0 | 2,580 | 2580 | 6,596 | 6,596 | 0% | yes | yes |
| 2026-05 | 1 | 0 | 4,697 | 4697 | 6,955 | 6,955 | 0% | yes | yes |
| 2026-09 | 13 | 0 | 202,872 | 15606 | - | - | - | yes |  |

### KXNGASMAX - Natural gas price peak

cadence longer; ladder {"CUMUL": 21}; settled 14, with expiration_value 14 (markets closing 2024-01 .. 2025-12); ticker formats {"old": 19, "none": 2}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2024-01 | 6 | 0 | 37,340 | 6223 | 98 | 6,486 | 0% | yes |  |
| 2025-01 | 4 | 0 | 36,002 | 9000 | 732 | 18,849 | 0% | yes | yes |
| 2025-11 | 2 | 0 | 616 | 308 | 720 | 1,006 | 0% | yes | yes |
| 2025-12 | 2 | 0 | 3,038 | 1519 | 37,837 | 52,703 | 0% | yes | yes |
| 2026-09 | 7 | 0 | 130,487 | 18641 | - | - | - | yes |  |

### KXDIESELW - diesel price week

cadence weekly; ladder {"CUMUL": 197}; settled 145, with expiration_value 145 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 197}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 115 | 21 | 100,878 | 877 | 1,146 | 3,810 | 34% | yes | yes |
| 2026-09 | 82 | 0 | 85,243 | 1040 | 1,364 | 5,771 | 32% | yes | yes |

### KXAAAGASMINTX - Texas lowest gas price yearly

cadence longer; ladder {"CUMUL": 13}; settled 7, with expiration_value 7 (markets closing 2023-10 .. 2025-12); ticker formats {"old": 13}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-10 | 1 | 0 | 28 | 28 | 1,280 | 1,280 | 0% |  |  |
| 2024-12 | 3 | 0 | 1,293 | 431 | 5,826 | 15,950 | 0% | yes | yes |
| 2025-12 | 3 | 0 | 87,531 | 29177 | 36,883 | 84,901 | 0% | yes | yes |
| 2026-09 | 6 | 0 | 95,742 | 15957 | - | - | - | yes |  |

### KXDIESELD - Daily Diesel Price

cadence daily; ladder {"CUMUL": 894}; settled 873, with expiration_value 873 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 894}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 619 | 0 | 122,946 | 199 | 1,002 | 3,203 | 17% | yes | yes |
| 2026-09 | 275 | 0 | 58,794 | 214 | 1,312 | 3,462 | 16% | yes | yes |

### KXCORNW - Corn Weekly

cadence weekly; ladder {"CUMUL": 140}; settled 140, with expiration_value 120 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 140}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 100 | 0 | 114,509 | 1145 | 77 | 1,887 | 24% | yes |  |
| 2026-05 | 40 | 0 | 58,062 | 1452 | 396 | 941 | 8% | yes | yes |

### KXLITHIUMMON - Lithium Monthly

cadence monthly; ladder {"CUMUL": 40}; settled 40, with expiration_value 40 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 40}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 40 | 0 | 167,367 | 4184 | 39 | 220 | 25% | yes |  |

### KXNICKELMON - Nickel Monthly

cadence monthly; ladder {"CUMUL": 40}; settled 40, with expiration_value 40 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 40}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 40 | 0 | 165,362 | 4134 | 210 | 430 | 0% | yes | yes |

### KXOILRIGS - Oil rigs

cadence unknown; ladder {"CUMUL": 23}; settled 11, with expiration_value 11 (markets closing 2025-12 .. 2025-12); ticker formats {"none": 23}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2025-12 | 11 | 0 | 134,735 | 12249 | 11,699 | 77,263 | 9% | yes | yes |
| 2026-09 | 12 | 0 | 9,568 | 797 | - | - | - | yes |  |

### KXNICKELW - Nickel Weekly

cadence weekly; ladder {"CUMUL": 170}; settled 170, with expiration_value 131 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 170}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 130 | 0 | 112,675 | 867 | 22 | 497 | 31% | yes |  |
| 2026-05 | 40 | 0 | 27,657 | 691 | 165 | 389 | 30% | yes | yes |

### KXSUGARMON - Sugar Monthly

cadence monthly; ladder {"CUMUL": 34}; settled 34, with expiration_value 34 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 34}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 34 | 0 | 134,021 | 3942 | 222 | 2,482 | 9% | yes | yes |

### KXCOFFEEW - Weekly Coffee Price

cadence weekly; ladder {"CUMUL": 126}; settled 126, with expiration_value 126 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 126}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 92 | 0 | 82,198 | 893 | 142 | 1,550 | 2% | yes | yes |
| 2026-05 | 34 | 0 | 48,036 | 1413 | 179 | 279 | 26% | yes | yes |

### KXLITHIUMW - Lithium Weekly

cadence weekly; ladder {"CUMUL": 190}; settled 190, with expiration_value 151 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 190}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 140 | 0 | 98,939 | 707 | 4 | 623 | 46% | yes |  |
| 2026-05 | 50 | 0 | 30,402 | 608 | 205 | 1,314 | 6% | yes | yes |

### KXCORNMON - Corn Monthly

cadence monthly; ladder {"CUMUL": 24}; settled 24, with expiration_value 24 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 24}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 24 | 0 | 125,809 | 5242 | 917 | 1,845 | 0% | yes | yes |

### KXSOLAR - Solar capcity installation

cadence unknown; ladder {"CUMUL": 10}; settled 5, with expiration_value 5 (markets closing 2026-03 .. 2026-03); ticker formats {"none": 10}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 5 | 0 | 113,868 | 22774 | 25,642 | 47,394 | 0% | yes | yes |
| 2026-09 | 5 | 0 | 10,888 | 2178 | - | - | - | yes |  |

### KXSUGARW - Sugar Weekly

cadence weekly; ladder {"CUMUL": 116}; settled 116, with expiration_value 92 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 116}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 82 | 0 | 82,979 | 1012 | 99 | 1,397 | 13% | yes |  |
| 2026-05 | 34 | 0 | 40,865 | 1202 | 51 | 300 | 6% | yes |  |

### KXSOYBEANW - Soybean Weekly

cadence weekly; ladder {"CUMUL": 120}; settled 120, with expiration_value 120 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 120}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 90 | 0 | 88,235 | 980 | 40 | 2,336 | 19% | yes |  |
| 2026-05 | 30 | 0 | 34,308 | 1144 | 7 | 731 | 43% | yes |  |

### KXWHEATMON - Wheat Monthly

cadence monthly; ladder {"CUMUL": 24}; settled 24, with expiration_value 24 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 24}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 24 | 0 | 116,986 | 4874 | 520 | 1,512 | 0% | yes | yes |

### KXWHEATW - Wheat Weekly

cadence monthly; ladder {"CUMUL": 92}; settled 92, with expiration_value 92 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 92}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 58 | 0 | 68,764 | 1186 | 22 | 454 | 3% | yes |  |
| 2026-05 | 34 | 0 | 43,351 | 1275 | 217 | 689 | 15% | yes | yes |

### KXLCATTLEMON - Live Cattle Monthly

cadence monthly; ladder {"CUMUL": 24}; settled 24, with expiration_value 24 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 24}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 24 | 0 | 111,611 | 4650 | 558 | 3,507 | 0% | yes | yes |

### KXWTIMINM - WTI oil monthly low

cadence monthly; ladder {"CUMUL": 31}; settled 31, with expiration_value 31 (markets closing 2026-04 .. 2026-06); ticker formats {"old": 31}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 12 | 0 | 43,602 | 3634 | 25,313 | 228,499 | 0% | yes | yes |
| 2026-05 | 5 | 0 | 30,850 | 6170 | 70,330 | 231,257 | 0% | yes | yes |
| 2026-06 | 14 | 0 | 33,287 | 2378 | 3,014 | 5,899 | 0% | yes | yes |

### KXBTCVSGOLD - BTC vs Gold

cadence unknown; ladder {"CUMUL": 3}; settled 2, with expiration_value 2 (markets closing 2025-11 .. 2026-01); ticker formats {"none": 3}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2025-11 | 1 | 0 | 28,211 | 28211 | 333,080 | 333,080 | 0% | yes | yes |
| 2026-01 | 1 | 0 | 11,041 | 11041 | 446,595 | 446,595 | 0% | yes | yes |
| 2026-09 | 1 | 0 | 66,585 | 66585 | - | - | - | yes |  |

### KXHOILW - Heating Oil Weekly

cadence weekly; ladder {"CUMUL": 110}; settled 110, with expiration_value 91 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 110}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 90 | 0 | 71,085 | 790 | 162 | 1,075 | 11% | yes | yes |
| 2026-05 | 20 | 0 | 34,625 | 1731 | 288 | 483 | 0% | yes | yes |

### KXCOFFEEMON - Coffee Monthly

cadence monthly; ladder {"CUMUL": 20}; settled 20, with expiration_value 20 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 20}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 20 | 0 | 104,835 | 5242 | 545 | 5,451 | 0% | yes | yes |

### KXDIESELMON - Diesel Prices month

cadence unknown; ladder {"CUMUL": 52}; settled 21, with expiration_value 21 (markets closing 2026-08 .. 2026-08); ticker formats {"old": 52}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 21 | 0 | 39,551 | 1883 | 60 | 161 | 0% | yes |  |
| 2026-09 | 31 | 0 | 65,199 | 2103 | 890 | 3,083 | 26% | yes | yes |

### KXPOWERKWH - Average US electricity price this month

cadence monthly; ladder {"CUMUL": 31}; settled 24, with expiration_value 24 (markets closing 2026-06 .. 2026-08); ticker formats {"old": 31}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-06 | 6 | 0 | 3,982 | 664 | 958 | 2,749 | 0% | yes | yes |
| 2026-07 | 11 | 0 | 69,417 | 6311 | 1,556 | 5,624 | 0% | yes | yes |
| 2026-08 | 7 | 0 | 23,725 | 3389 | 878 | 1,242 | 0% | yes | yes |
| 2026-09 | 7 | 0 | 7,113 | 1016 | 5,052 | 12,628 | 0% | yes | yes |

### KXBARRELS - Oil barrels

cadence unknown; ladder {"CUMUL": 11}; settled 7, with expiration_value 7 (markets closing 2025-12 .. 2026-07); ticker formats {"none": 11}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2025-12 | 4 | 0 | 77,621 | 19405 | 6,653 | 26,463 | 0% | yes | yes |
| 2026-07 | 3 | 0 | 8,547 | 2849 | 3,874 | 7,610 | 0% | yes | yes |
| 2026-09 | 4 | 0 | 16,591 | 4148 | - | - | - | yes |  |

### KXCOCOAW - Cocoa Directional Weekly

cadence weekly; ladder {"CUMUL": 90}; settled 90, with expiration_value 90 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 90}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 70 | 0 | 61,944 | 885 | 171 | 1,718 | 10% | yes | yes |
| 2026-05 | 20 | 0 | 39,463 | 1973 | 32 | 266 | 10% | yes |  |

### KXSOYBEANMON - Soybean monthly

cadence monthly; ladder {"CUMUL": 20}; settled 20, with expiration_value 20 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 20}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 20 | 0 | 101,064 | 5053 | 390 | 1,598 | 0% | yes | yes |

### KXAAAGASED - US gas price on Election Day

cadence unknown; ladder {"CUMUL": 11}; settled 0, with expiration_value 0; ticker formats {"old": 11}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 11 | 0 | 98,555 | 8960 | - | - | - | yes |  |

### KXSPRLVL - SPR level on date

cadence weekly; ladder {"CUMUL": 140}; settled 128, with expiration_value 128 (markets closing 2026-04 .. 2026-09); ticker formats {"old": 140}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 21 | 0 | 28,644 | 1364 | 8,286 | 44,121 | 0% | yes | yes |
| 2026-07 | 37 | 0 | 31,652 | 855 | 2,874 | 5,688 | 0% | yes | yes |
| 2026-08 | 56 | 0 | 20,552 | 367 | 1,135 | 4,198 | 12% | yes | yes |
| 2026-09 | 26 | 0 | 15,148 | 583 | 1,279 | 2,699 | 0% | yes | yes |

### KXAAAGASMINFL - Florida lowest gas price yearly

cadence longer; ladder {"CUMUL": 7}; settled 3, with expiration_value 3 (markets closing 2025-12 .. 2026-01); ticker formats {"old": 7}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2025-12 | 2 | 0 | 9,205 | 4602 | 33,020 | 50,414 | 0% | yes | yes |
| 2026-01 | 1 | 0 | 27 | 27 | 0 | 0 | 100% |  |  |
| 2026-09 | 4 | 0 | 86,419 | 21605 | - | - | - | yes |  |

### KXLCATTLEW - Live Cattle Weekly

cadence weekly; ladder {"CUMUL": 90}; settled 90, with expiration_value 90 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 90}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 60 | 0 | 64,269 | 1071 | 190 | 2,979 | 3% | yes | yes |
| 2026-05 | 30 | 0 | 30,697 | 1023 | 143 | 524 | 17% | yes | yes |

### KXWTIDIRY - WTIDIRY

cadence longer; ladder {"CUMUL": 11}; settled 0, with expiration_value 0; ticker formats {"new": 11}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 11 | 0 | 92,478 | 8407 | - | - | - | yes |  |

### KXCOCOAMON - Cocoa Monthly

cadence monthly; ladder {"CUMUL": 24}; settled 24, with expiration_value 24 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 24}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 24 | 0 | 81,744 | 3406 | 276 | 2,048 | 4% | yes | yes |

### KXAAAGASMAXFL - Florida highest gas price yearly

cadence longer; ladder {"CUMUL": 19}; settled 12, with expiration_value 12 (markets closing 2025-12 .. 2026-05); ticker formats {"old": 19}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2025-12 | 2 | 0 | 8,128 | 4064 | 23,202 | 26,910 | 0% | yes | yes |
| 2026-02 | 1 | 0 | 154 | 154 | 180 | 180 | 0% | yes | yes |
| 2026-03 | 7 | 0 | 11,834 | 1691 | 635 | 19,425 | 0% | yes | yes |
| 2026-05 | 2 | 0 | 5,705 | 2852 | 17,828 | 28,167 | 0% | yes | yes |
| 2026-09 | 7 | 0 | 53,091 | 7584 | - | - | - | yes |  |

### KXAAAGASMIN - US lowest gas price yearly

cadence longer; ladder {"CUMUL": 15}; settled 6, with expiration_value 4 (markets closing 2023-11 .. 2026-07); ticker formats {"old": 15}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-11 | 1 | 0 | 65 | 65 | 1,826 | 1,826 | 0% | yes | yes |
| 2024-12 | 2 | 0 | 1,233 | 616 | 3,666 | 6,370 | 0% | yes | yes |
| 2025-12 | 2 | 2 | 0 | 0 | 0 | 0 | 100% |  |  |
| 2026-07 | 1 | 0 | 8,950 | 8950 | 8,031 | 8,031 | 0% | yes | yes |
| 2026-09 | 9 | 0 | 68,364 | 7596 | - | - | - | yes |  |

### KXAAAGASDFL - Florida gas price

cadence daily; ladder {"CUMUL": 376}; settled 359, with expiration_value 359 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 376}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 113 | 0 | 18,645 | 165 | 1,978 | 5,226 | 4% | yes | yes |
| 2026-09 | 263 | 0 | 59,733 | 227 | 1,818 | 6,439 | 8% | yes | yes |

### KXWTIWHEN - WTI When

cadence unknown; ladder {"CUMUL": 17}; settled 8, with expiration_value 8 (markets closing 2026-07 .. 2026-08); ticker formats {"none": 17}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-07 | 6 | 0 | 27,655 | 4609 | 5,009 | 6,689 | 0% | yes | yes |
| 2026-08 | 5 | 0 | 28,723 | 5745 | 2,684 | 4,902 | 0% | yes | yes |
| 2026-09 | 6 | 0 | 20,616 | 3436 | 8,967 | 9,034 | 0% | yes | yes |

### KXAAAGASDTX - TX gas price

cadence daily; ladder {"CUMUL": 373}; settled 346, with expiration_value 346 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 373}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 136 | 0 | 18,427 | 135 | 1,228 | 3,303 | 7% | yes | yes |
| 2026-09 | 237 | 0 | 50,501 | 213 | 1,285 | 3,558 | 8% | yes | yes |

### KXRHGOLD - RH gold

cadence unknown; ladder {"CUMUL": 47}; settled 47, with expiration_value 42 (markets closing 2024-05 .. 2025-10); ticker formats {"none": 47}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2024-05 | 10 | 5 | 263 | 26 | 0 | 2,258 | 70% |  |  |
| 2024-08 | 8 | 0 | 343 | 43 | 1,448 | 4,736 | 0% |  |  |
| 2024-10 | 5 | 0 | 373 | 75 | 709 | 794 | 0% | yes | yes |
| 2025-02 | 5 | 0 | 19,268 | 3854 | 5,138 | 13,026 | 0% | yes | yes |
| 2025-04 | 1 | 0 | 2,238 | 2238 | 8,372 | 8,372 | 0% | yes | yes |
| 2025-05 | 8 | 0 | 8,697 | 1087 | 282 | 3,032 | 25% | yes | yes |
| 2025-07 | 3 | 0 | 22,691 | 7564 | 2,375 | 8,895 | 0% | yes | yes |
| 2025-10 | 7 | 0 | 14,206 | 2029 | 0 | 17 | 86% | yes |  |

### KXJETFUEL - US Gulf Coast jet fuel price weekly

cadence weekly; ladder {"CUMUL": 131}; settled 131, with expiration_value 131 (markets closing 2026-04 .. 2026-07); ticker formats {"old": 131}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 24 | 0 | 7,999 | 333 | 445 | 2,030 | 4% | yes | yes |
| 2026-05 | 44 | 0 | 22,186 | 504 | 49 | 2,717 | 25% | yes |  |
| 2026-06 | 44 | 0 | 27,829 | 632 | 69 | 2,724 | 23% | yes |  |
| 2026-07 | 19 | 0 | 9,798 | 516 | 26 | 844 | 21% | yes |  |

### KXAAAGASDIL - Illinois gas price

cadence daily; ladder {"CUMUL": 309}; settled 292, with expiration_value 292 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 309}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 102 | 0 | 19,320 | 189 | 1,511 | 3,097 | 1% | yes | yes |
| 2026-09 | 207 | 0 | 46,545 | 225 | 1,257 | 3,361 | 12% | yes | yes |

### KXHOILMON - Heating Oil Monthly

cadence monthly; ladder {"CUMUL": 20}; settled 20, with expiration_value 20 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 20}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-04 | 20 | 0 | 60,852 | 3043 | 660 | 1,734 | 0% | yes | yes |

### KXAAAGASDOH - Ohio gas price

cadence daily; ladder {"CUMUL": 270}; settled 243, with expiration_value 243 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 270}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 270 | 0 | 58,356 | 216 | 1,139 | 3,706 | 11% | yes | yes |

### KXNGASMIN - Natural gas yearly low

cadence longer; ladder {"CUMUL": 14}; settled 9, with expiration_value 9 (markets closing 2023-01 .. 2026-05); ticker formats {"old": 14}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2023-01 | 3 | 0 | 73 | 24 | 100 | 1,441 | 33% |  |  |
| 2023-02 | 1 | 0 | 502 | 502 | 1,081 | 1,081 | 0% | yes | yes |
| 2025-12 | 3 | 0 | 6,570 | 2190 | 3,665 | 16,583 | 0% | yes | yes |
| 2026-05 | 2 | 0 | 2,905 | 1452 | 9,506 | 14,856 | 0% | yes | yes |
| 2026-09 | 5 | 0 | 45,635 | 9127 | - | - | - | yes |  |

### KXNGAS - Natural gas price max and min monthly

cadence monthly; ladder {"CUMUL": 16}; settled 16, with expiration_value 16 (markets closing 2022-03 .. 2022-08); ticker formats {"old": 16}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2022-03 | 1 | 0 | 293 | 293 | 15,907 | 15,907 | 0% | yes | yes |
| 2022-04 | 2 | 0 | 26 | 13 | 583 | 915 | 0% |  |  |
| 2022-06 | 4 | 0 | 3,514 | 878 | 4,438 | 10,325 | 0% | yes | yes |
| 2022-07 | 6 | 0 | 29,643 | 4940 | 2,044 | 4,820 | 17% | yes | yes |
| 2022-08 | 3 | 0 | 22,136 | 7379 | 26 | 1,632 | 0% | yes |  |

### KXAAAGASDCA - California gas price

cadence daily; ladder {"CUMUL": 309}; settled 292, with expiration_value 292 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 309}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 102 | 0 | 18,106 | 178 | 1,765 | 3,820 | 4% | yes | yes |
| 2026-09 | 207 | 0 | 37,044 | 179 | 1,255 | 2,939 | 4% | yes | yes |

### KXDXYVSGOLD - DXY vs. Gold

cadence longer; ladder {"RANGE": 2}; settled 0, with expiration_value 0; ticker formats {"old": 2}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 2 | 0 | 51,536 | 25768 | - | - | - | yes |  |

### KXAAAGASDNJ - New Jersey gas prices

cadence daily; ladder {"CUMUL": 326}; settled 299, with expiration_value 299 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 326}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 102 | 0 | 14,047 | 138 | 1,356 | 3,123 | 4% | yes | yes |
| 2026-09 | 224 | 0 | 37,423 | 167 | 1,344 | 3,697 | 5% | yes | yes |

### KXGOLDVSSILVER - Gold vs. Silver

cadence longer; ladder {"RANGE": 2}; settled 0, with expiration_value 0; ticker formats {"old": 2}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 2 | 0 | 48,115 | 24058 | - | - | - | yes |  |

### KXAAAGASDWA - Washington gas price

cadence daily; ladder {"CUMUL": 174}; settled 157, with expiration_value 157 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 174}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 174 | 0 | 44,876 | 258 | 1,105 | 4,147 | 12% | yes | yes |

### KXAAAGASWNJ - New Jersey gas price this week

cadence weekly; ladder {"CUMUL": 74}; settled 53, with expiration_value 53 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 74}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 21 | 0 | 30,988 | 1476 | 4,715 | 6,365 | 0% | yes | yes |
| 2026-09 | 53 | 0 | 11,405 | 215 | 400 | 1,050 | 6% | yes | yes |

### KXAAAGASDGA - Georgia gas price

cadence daily; ladder {"CUMUL": 182}; settled 165, with expiration_value 165 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 182}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 182 | 0 | 41,866 | 230 | 1,235 | 3,476 | 8% | yes | yes |

### KXTXOIL - Texas crude oil production

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"old": 4}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 4 | 0 | 40,952 | 10238 | - | - | - | yes |  |

### KXDIESELYE - Diesel prices at year end

cadence longer; ladder {"CUMUL": 19}; settled 0, with expiration_value 0; ticker formats {"old": 19}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 19 | 0 | 37,536 | 1976 | - | - | - | yes |  |

### KXAAAGASDNY - New York gas price

cadence daily; ladder {"CUMUL": 289}; settled 272, with expiration_value 272 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 289}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 102 | 0 | 10,236 | 100 | 1,528 | 2,505 | 2% | yes | yes |
| 2026-09 | 187 | 0 | 27,220 | 146 | 1,100 | 2,837 | 6% | yes | yes |

### KXIRANCRUDE - Iran crude oil production in [month]

cadence monthly; ladder {"CUMUL": 45}; settled 34, with expiration_value 34 (markets closing 2026-07 .. 2026-09); ticker formats {"old": 45}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-07 | 12 | 0 | 20,620 | 1718 | 613 | 902 | 0% | yes | yes |
| 2026-08 | 11 | 0 | 10,195 | 927 | 158 | 837 | 0% | yes | yes |
| 2026-09 | 22 | 0 | 6,300 | 286 | 19 | 518 | 36% | yes |  |

### KXAAAGASDNC - North Carolina gas price

cadence daily; ladder {"CUMUL": 180}; settled 163, with expiration_value 163 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 180}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 180 | 0 | 36,864 | 205 | 1,123 | 2,768 | 10% | yes | yes |

### KXAAAGASDPA - Pennsylvania gas price

cadence daily; ladder {"CUMUL": 210}; settled 193, with expiration_value 193 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 210}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 210 | 0 | 36,682 | 175 | 1,215 | 3,341 | 10% | yes | yes |

### KXILNUCLEAR - Illinois nuclear electricity generation

cadence longer; ladder {"CUMUL": 7}; settled 0, with expiration_value 0; ticker formats {"old": 7}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 7 | 0 | 36,333 | 5190 | - | - | - | yes |  |

### KXDIESELELECT - Diesel prices on Election Day

cadence unknown; ladder {"CUMUL": 15}; settled 0, with expiration_value 0; ticker formats {"old": 15}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 15 | 0 | 34,352 | 2290 | - | - | - | yes |  |

### KXPJMEMERGENCY - PJM capacity emergency days

cadence longer; ladder {"CUMUL": 6}; settled 1, with expiration_value 1 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 6}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 6 | 0 | 33,944 | 5657 | 12,756 | 12,756 | 0% | yes | yes |

### KXTXERCOTPEAK - Texas ERCOT peak electricity demand

cadence unknown; ladder {"CUMUL": 7}; settled 0, with expiration_value 0; ticker formats {"old": 7}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 7 | 0 | 30,533 | 4362 | - | - | - | yes |  |

### KXWTIMAXM - WTI oil monthly high

cadence monthly; ladder {"CUMUL": 14}; settled 14, with expiration_value 14 (markets closing 2026-06 .. 2026-06); ticker formats {"old": 14}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-06 | 14 | 0 | 30,074 | 2148 | 1,652 | 5,460 | 0% | yes | yes |

### KXAKPFD - Alaska Permanent Fund Dividend

cadence longer; ladder {"CUMUL": 5}; settled 0, with expiration_value 0; ticker formats {"old": 5}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 5 | 0 | 28,663 | 5733 | - | - | - | yes |  |

### KXINXVSBTC - Will the S&P 500 outperform gold this year?

cadence longer; ladder {"RANGE": 2}; settled 0, with expiration_value 0; ticker formats {"old": 2}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 2 | 0 | 27,725 | 13862 | - | - | - | yes |  |

### KXTXERCOTPEAKD - Texas ERCOT peak electricity demand

cadence daily; ladder {"CUMUL": 175}; settled 163, with expiration_value 163 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 175}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 35 | 0 | 4,380 | 125 | 2,025 | 9,169 | 0% | yes | yes |
| 2026-09 | 140 | 0 | 21,334 | 152 | 2,000 | 8,632 | 0% | yes | yes |

### KXDIESELMAXY - Highest U.S. diesel price by year

cadence longer; ladder {"CUMUL": 12}; settled 0, with expiration_value 0; ticker formats {"old": 12}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 12 | 0 | 24,876 | 2073 | - | - | - | yes |  |

### KXTRUFGAS - Truflation US CPI Gasoline Price Index

cadence daily; ladder {"CUMUL": 165}; settled 165, with expiration_value 165 (markets closing 2026-06 .. 2026-08); ticker formats {"old": 165}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-06 | 150 | 0 | 12,581 | 84 | 13 | 112 | 20% | yes |  |
| 2026-08 | 15 | 0 | 12,086 | 806 | 31 | 150 | 13% | yes |  |

### KXMEXCUBOIL - Mexico resumes oil exports to Cuba before date

cadence unknown; ladder {"CUMUL": 4}; settled 2, with expiration_value 2 (markets closing 2026-07 .. 2026-08); ticker formats {"none": 4}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-07 | 1 | 0 | 18,862 | 18862 | 32,887 | 32,887 | 0% | yes | yes |
| 2026-08 | 1 | 0 | 944 | 944 | 2,041 | 2,041 | 0% | yes | yes |
| 2026-09 | 2 | 0 | 2,481 | 1240 | 2,426 | 2,426 | 0% | yes | yes |

### KXOILW - Price of oil weekly

cadence weekly; ladder {"CUMUL": 30}; settled 30, with expiration_value 30 (markets closing 2022-03 .. 2022-08); ticker formats {"old": 30}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2022-03 | 8 | 0 | 2,597 | 325 | 1,569 | 9,226 | 0% | yes | yes |
| 2022-04 | 4 | 0 | 8,343 | 2086 | 368 | 1,306 | 0% | yes | yes |
| 2022-05 | 4 | 0 | 2,616 | 654 | 1,560 | 2,430 | 0% | yes | yes |
| 2022-06 | 4 | 0 | 3,189 | 797 | 1,690 | 3,718 | 0% | yes | yes |
| 2022-07 | 4 | 0 | 1,547 | 387 | 702 | 2,570 | 0% | yes | yes |
| 2022-08 | 6 | 0 | 3,677 | 613 | 1,967 | 5,356 | 17% | yes | yes |

### KXDIESELMINY - Lowest U.S. diesel price by year

cadence longer; ladder {"CUMUL": 12}; settled 0, with expiration_value 0; ticker formats {"old": 12}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 12 | 0 | 21,770 | 1814 | - | - | - | yes |  |

### KXKSWHEAT - Kansas wheat production

cadence longer; ladder {"CUMUL": 8}; settled 0, with expiration_value 0; ticker formats {"old": 8}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 8 | 0 | 19,986 | 2498 | 1,006 | 8,142 | 25% | yes | yes |

### KXWTIVSBRENT - Will the WTI outperform Brent this year?

cadence unknown; ladder {"RANGE": 2}; settled 0, with expiration_value 0; ticker formats {"old": 2}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 2 | 0 | 19,840 | 9920 | - | - | - | yes |  |

### KXOPECCUTS - Oil production cuts

cadence unknown; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2026-01 .. 2026-01); ticker formats {"none": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-01 | 1 | 0 | 19,734 | 19734 | 7,539 | 7,539 | 0% | yes | yes |

### KXSPRMIN - SPRMIN

cadence unknown; ladder {"CUMUL": 2}; settled 2, with expiration_value 2 (markets closing 2025-01 .. 2026-01); ticker formats {"none": 2}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2025-01 | 1 | 0 | 2,605 | 2605 | 5,920 | 5,920 | 0% | yes | yes |
| 2026-01 | 1 | 0 | 16,929 | 16929 | 17,940 | 17,940 | 0% | yes | yes |

### KXB65 - Beef 65

cadence unknown; ladder {"CUMUL": 33}; settled 22, with expiration_value 22 (markets closing 2026-08 .. 2026-09); ticker formats {"none": 33}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 11 | 0 | 6,996 | 636 | 125 | 421 | 0% | yes | yes |
| 2026-09 | 22 | 0 | 11,126 | 506 | 24 | 43 | 0% | yes |  |

### KXINXVSGOLD - Will the S&P 500 outperform gold this year?

cadence longer; ladder {"RANGE": 2}; settled 0, with expiration_value 0; ticker formats {"old": 2}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 2 | 0 | 16,911 | 8456 | - | - | - | yes |  |

### KXB85 - B85

cadence unknown; ladder {"CUMUL": 33}; settled 22, with expiration_value 22 (markets closing 2026-08 .. 2026-09); ticker formats {"none": 33}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 11 | 0 | 5,107 | 464 | 161 | 329 | 0% | yes | yes |
| 2026-09 | 22 | 0 | 9,783 | 445 | 46 | 107 | 0% | yes |  |

### KXIAETHANOL - Iowa ethanol production

cadence longer; ladder {"CUMUL": 8}; settled 0, with expiration_value 0; ticker formats {"old": 8}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 8 | 0 | 14,852 | 1856 | - | - | - | yes |  |

### KXMARCELLUSGAS - Marcellus natural gas production

cadence longer; ladder {"CUMUL": 6}; settled 0, with expiration_value 0; ticker formats {"old": 6}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 6 | 0 | 14,791 | 2465 | - | - | - | yes |  |

### KXSDCORNYIELD - South Dakota corn yield

cadence longer; ladder {"CUMUL": 8}; settled 0, with expiration_value 0; ticker formats {"old": 8}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 8 | 0 | 14,668 | 1834 | - | - | - | yes |  |

### KXOPUS48OY - Opus 4.8 Output Token

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 4 | 0 | 14,048 | 3512 | - | - | - | yes |  |

### KXWICORNYIELD - Wisconsin corn yield

cadence unknown; ladder {"CUMUL": 9}; settled 0, with expiration_value 0; ticker formats {"old": 9}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 9 | 0 | 13,688 | 1521 | - | - | - | yes |  |

### KXRIRESPOWER - Rhode Island residential electricity price

cadence longer; ladder {"CUMUL": 7}; settled 0, with expiration_value 0; ticker formats {"old": 7}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 7 | 0 | 13,636 | 1948 | - | - | - | yes |  |

### KXWYCOAL - Wyoming coal production

cadence unknown; ladder {"CUMUL": 8}; settled 0, with expiration_value 0; ticker formats {"old": 8}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 8 | 0 | 12,914 | 1614 | - | - | - | yes |  |

### KXAAAGASMAXM - US highest gas price monthly

cadence monthly; ladder {"CUMUL": 9}; settled 1, with expiration_value 1 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 9}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 9 | 0 | 12,908 | 1434 | 6,108 | 6,143 | 0% | yes | yes |

### KXWVCOAL - West Virginia coal production

cadence longer; ladder {"CUMUL": 7}; settled 0, with expiration_value 0; ticker formats {"old": 7}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 7 | 0 | 12,178 | 1740 | - | - | - | yes |  |

### KXGBT55OY - GPT 5.5 Input Token

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 4 | 0 | 11,088 | 2772 | - | - | - | yes |  |

### KXGOLD - Price of gold

cadence daily; ladder {"RANGE": 95}; settled 95, with expiration_value 19 (markets closing 2022-09 .. 2022-10); ticker formats {"new": 95}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2022-09 | 75 | 0 | 8,486 | 113 | 5 | 987 | 45% | yes |  |
| 2022-10 | 20 | 0 | 2,389 | 119 | 472 | 4,465 | 0% | yes | yes |

### KXAAAGASMINM - US lowest gas price monthly

cadence monthly; ladder {"CUMUL": 9}; settled 0, with expiration_value 0; ticker formats {"old": 9}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 9 | 0 | 10,498 | 1166 | - | - | - | yes |  |

### KXMSCOTTON - Mississippi cotton production

cadence longer; ladder {"CUMUL": 6}; settled 0, with expiration_value 0; ticker formats {"old": 6}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 6 | 0 | 10,267 | 1711 | - | - | - | yes |  |

### KXNGASW - Natural gas price max and min weekly

cadence weekly; ladder {"CUMUL": 13}; settled 13, with expiration_value 13 (markets closing 2022-07 .. 2022-08); ticker formats {"old": 13}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2022-07 | 7 | 0 | 5,169 | 738 | 803 | 5,756 | 14% | yes | yes |
| 2022-08 | 6 | 0 | 4,575 | 762 | 1,338 | 2,616 | 0% | yes | yes |

### KXKYCOAL - Kentucky coal production

cadence longer; ladder {"CUMUL": 6}; settled 0, with expiration_value 0; ticker formats {"old": 6}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 6 | 0 | 9,450 | 1575 | - | - | - | yes |  |

### KXNECORNYIELD - Nebraska corn yield

cadence longer; ladder {"CUMUL": 5}; settled 0, with expiration_value 0; ticker formats {"old": 5}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 5 | 0 | 8,671 | 1734 | - | - | - | yes |  |

### KXAAAGASDTN - Tennessee gas price

cadence daily; ladder {"CUMUL": 44}; settled 27, with expiration_value 27 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 44}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 44 | 0 | 7,848 | 178 | 103 | 2,440 | 48% | yes | yes |

### KXINCORNYIELD - Indiana corn yield

cadence unknown; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 7,822 | 7822 | - | - | - | yes |  |

### KXSPRUSE - SPR use

cadence unknown; ladder {"CUMUL": 3}; settled 3, with expiration_value 3 (markets closing 2025-07 .. 2025-09); ticker formats {"none": 3}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2025-07 | 1 | 0 | 935 | 935 | 2,069 | 2,069 | 0% | yes | yes |
| 2025-08 | 1 | 0 | 2,843 | 2843 | 6,795 | 6,795 | 0% | yes | yes |
| 2025-09 | 1 | 0 | 3,992 | 3992 | 11,389 | 11,389 | 0% | yes | yes |

### KXIACORN - Iowa corn production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 7,652 | 7652 | - | - | - | yes |  |

### KXVENEZCRUDE - Venezuela crude oil production in [month]

cadence monthly; ladder {"CUMUL": 8}; settled 0, with expiration_value 0; ticker formats {"old": 8}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 8 | 0 | 7,607 | 951 | - | - | - | yes |  |

### KXNMCOIL - New Mexico crude oil production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 7,128 | 7128 | - | - | - | yes |  |

### KXGEMINI35OY - Gemini 3.5 Flash Output Token

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 4 | 0 | 6,940 | 1735 | - | - | - | yes |  |

### KXAAAGASDVA - Virginia gas price

cadence daily; ladder {"CUMUL": 44}; settled 27, with expiration_value 27 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 44}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 44 | 0 | 5,387 | 122 | 9 | 1,300 | 48% | yes |  |

### KXAAAGASDAZ - Arizona gas price

cadence daily; ladder {"CUMUL": 34}; settled 17, with expiration_value 17 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 34}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 34 | 0 | 5,339 | 157 | 100 | 2,047 | 38% | yes | yes |

### KXPAGAS - Pennsylvania natural gas production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 5,316 | 5316 | - | - | - | yes |  |

### KXAAAGASDMA - Massachusetts gas price

cadence daily; ladder {"CUMUL": 34}; settled 17, with expiration_value 17 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 34}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 34 | 0 | 4,896 | 144 | 0 | 1,100 | 65% | yes |  |

### KXAAAGASDMI - Michigan gas price

cadence daily; ladder {"CUMUL": 34}; settled 17, with expiration_value 17 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 34}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 34 | 0 | 4,605 | 135 | 190 | 1,551 | 38% | yes | yes |

### KXNDKOIL - North Dakota crude oil production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 3,782 | 3782 | - | - | - | yes |  |

### KXAKCRUDEOIL - Alaska crude oil production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 3,741 | 3741 | - | - | - | yes |  |

### KXRUCRUDEX - Russia crude exports in [month] below x.x mbpd?

cadence unknown; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2026-05 .. 2026-05); ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-05 | 1 | 0 | 3,711 | 3711 | 19,982 | 19,982 | 0% | yes | yes |

### KXGEMINI35Y - Gemini 3.5 Flash

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 4 | 0 | 3,620 | 905 | - | - | - | yes |  |

### KXOPUS48Y - Opus 4.8 Input Token

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 4 | 0 | 3,498 | 874 | - | - | - | yes |  |

### KXGPT55Y - GPT 5.5 Input Token

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 4 | 0 | 3,466 | 866 | - | - | - | yes |  |

### KXEIACRUDEW - U.S. crude oil inventories

cadence weekly; ladder {"CUMUL": 26}; settled 13, with expiration_value 13 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 26}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 26 | 0 | 2,920 | 112 | 0 | 0 | 96% | yes |  |

### KXLAOILGASEMP - Louisiana oil and gas extraction employment

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 2,737 | 2737 | - | - | - | yes |  |

### KXDOESPRTENDER - DOE Strategic Petroleum Reserve tenders

cadence unknown; ladder {"CUMUL": 3}; settled 0, with expiration_value 0; ticker formats {"none": 3}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 3 | 0 | 2,607 | 869 | - | - | - | yes |  |

### KXNECOF - Nebraska cattle on feed

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 2,169 | 2169 | - | - | - | yes |  |

### KXVERARELEASE - Vera /rubin release

cadence unknown; ladder {"CUMUL": 6}; settled 2, with expiration_value 2 (markets closing 2026-08 .. 2026-09); ticker formats {"none": 6}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 1 | 0 | 46 | 46 | 0 | 0 | 100% |  |  |
| 2026-09 | 5 | 0 | 1,910 | 382 | 7 | 7 | 0% | yes |  |

### KXOKOIL - Oklahoma crude oil production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 1,716 | 1716 | - | - | - | yes |  |

### KXBOEGOLD - BOE gold withdrawals

cadence unknown; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2025-05 .. 2025-05); ticker formats {"none": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2025-05 | 1 | 0 | 1,677 | 1677 | 2,941 | 2,941 | 0% | yes | yes |

### KXSDCATTLE - South Dakota cattle inventory

cadence unknown; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 1,438 | 1438 | - | - | - | yes |  |

### KXAAAEVM - US EV charging price

cadence monthly; ladder {"CUMUL": 11}; settled 11, with expiration_value 11 (markets closing 2026-08 .. 2026-08); ticker formats {"old": 11}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-08 | 11 | 0 | 1,238 | 113 | 1 | 22 | 27% | yes |  |

### KXMTCATTLE - Montana cattle inventory

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 1 | 0 | 1,238 | 1238 | - | - | - | yes |  |

### KXKEYSTONEFID - Keystone XL final investment decision

cadence unknown; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 4 | 0 | 897 | 224 | - | - | - | yes |  |

### KXCHINAOILINV - China strategic oil inventories

cadence unknown; ladder {"CUMUL": 5}; settled 0, with expiration_value 0; ticker formats {"old": 5}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09 | 5 | 0 | 775 | 155 | - | - | - | yes |  |

### KXDIESELM - Diesel price this month

cadence monthly; ladder {"CUMUL": 10}; settled 10, with expiration_value 10 (markets closing 2022-11 .. 2022-11); ticker formats {"old": 10}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2022-11 | 10 | 0 | 722 | 72 | 1,542 | 3,955 | 0% | yes | yes |

### KXDIESEL - Diesel price this week

cadence weekly; ladder {"CUMUL": 26}; settled 26, with expiration_value 26 (markets closing 2022-10 .. 2022-12); ticker formats {"old": 26}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2022-10 | 9 | 0 | 297 | 33 | 575 | 1,216 | 22% |  |  |
| 2022-11 | 9 | 0 | 194 | 22 | 200 | 419 | 0% |  |  |
| 2022-12 | 8 | 0 | 210 | 26 | 140 | 1,374 | 50% |  |  |

### KXSTEELMON - Steel Monthly Price

cadence monthly; ladder {"RANGE": 80}; settled 40, with expiration_value 11 (markets closing 2026-03 .. 2026-03); ticker formats {"new": 40, "none": 40}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 80 | 40 | 40 | 0 | 0 | 0 | 100% |  |  |

### KXWHEAT - Average wheat price

cadence monthly; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2022-04 .. 2022-04); ticker formats {"none": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2022-04 | 1 | 0 | 31 | 31 | 577 | 577 | 0% |  |  |

### KXWTIEU - WTI oil up after election

cadence unknown; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2024-11 .. 2024-11); ticker formats {"old": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2024-11 | 1 | 0 | 15 | 15 | 30 | 30 | 0% |  |  |

### KXIEAOIL - Will the IEA approve a strategic oil reserves release?

cadence unknown; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2026-03 .. 2026-03); ticker formats {"none": 1}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 1 | 0 | 12 | 12 | 200 | 200 | 0% |  |  |

### KXWTIE - WTI oil election day

cadence unknown; ladder {"CUMUL": 15}; settled 15, with expiration_value 15 (markets closing 2024-11 .. 2024-11); ticker formats {"old": 15}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2024-11 | 15 | 11 | 10 | 1 | 0 | 0 | 93% |  |  |

### KXSTEELW - Steel Weekly Price

cadence weekly; ladder {"CUMUL": 80}; settled 0, with expiration_value 0; ticker formats {"new": 40, "none": 40}

| month | markets | zero-candle | candles | per market | median vol | p90 vol | zero-vol | quoted | tradeable |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-03 | 80 | 80 | 0 | 0 | 0 | 0 | 100% |  |  |
