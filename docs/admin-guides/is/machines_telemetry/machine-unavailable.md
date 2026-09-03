---
id: machine-unavailable
locale: is
translation_status: review
title: "Vélin sýnist upptekin þótt hún sé laus"
summary: "Ein vél er áfram merkt In use á skjánum þótt enginn sé að nota hana."
search_aliases:
  - vél föst sem upptekin
  - vélin sýnir upptekin en er tóm
  - ekki hægt að velja vél
  - vélarspjaldið er grátt
checks:
  - id: machine-run-state
    question: "Í hvaða run state heldur bakendinn þessari vél?"
    look_for: "Diagnostics, Live readings, Run state á spjaldi vélarinnar."
    expected: "available fyrir lausa vél. in_use eða offline skýrir merkinguna á skjánum."
    route: diagnostics
    diagnostics: machine.identity
  - id: machine-pending-start
    question: "Heldur vélin enn frátekningu frá fyrra vali?"
    look_for: "Diagnostics, Live readings, Pending start."
    expected: "Nei. Já þýðir að vélin er frátekin og frátekningin er ekki runnin út."
    route: diagnostics
    diagnostics: machine.identity
    problem_guide: machine-does-not-start
  - id: machine-last-reading
    question: "Er enn verið að lesa vélina og hvert er gildið?"
    look_for: "Diagnostics, Live readings, gildið og Last read."
    expected: "Tala sem uppfærist um það bil jafn oft og poll interval vélarinnar."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: machine-band
    question: "Hvar liggur mælingin miðað við þröskuldana?"
    look_for: "Diagnostics, Live readings, bandtextinn undir gildinu."
    expected: "at or below OFF threshold fyrir lausa vél."
    route: diagnostics
    diagnostics: machine.thresholds
  - id: telemetry-polling-on
    question: "Er fjarmæling í gangi?"
    look_for: "Viðvörunarborðinn efst í Diagnostics og Telemetry á Overview."
    expected: "Enabled, og enginn borði um að slökkt sé á fjarmælingu."
    route: diagnostics
    diagnostics: settings.telemetry
    problem_guide: all-machines-available-telemetry-stale
---

## Hvenær á að nota þetta {#when-to-use}

Notaðu þessa leiðbeiningu þegar **ein** vél sýnir sig áfram sem *In use* á
skjánum og ekki er hægt að velja hana, á meðan vélin sjálf stendur ónotuð. Aðrar
vélar haga sér eðlilega.

Ef **allar** vélar sýnast lausar og viðskiptavinum er vísað á vélar sem eru
þegar í gangi, þá er þetta röng leiðbeining. Lestu þá
[Allar vélar sýnast lausar þegar fjarmæling er stöðnuð](guide:all-machines-available-telemetry-stale).

Vél sem hefur verið slökkt á í stjórnborðinu lítur ekki svona út. Hún hverfur
alveg af skjánum í stað þess að sýnast upptekin.

## Mögulegar orsakir {#causes}

Skjárinn leyfir val á vél aðeins þegar bakendinn heldur henni sem *available*
**og** engin frátekning hvílir á henni. Þrjú ástönd valda merkingunni sem þú ert
að horfa á.

**Vélin er enn frátekin.** Þegar viðskiptavinur velur vél heldur bakendinn
frátekningu á henni þar til fjarmæling staðfestir ræsingu eða frátekningin
rennur út eftir `machine_reservation_minutes`. Val sem varð aldrei að raunverulegri
ræsingu lokar því vélinni út þann tíma.

**Bakendinn telur vélina vera í gangi.** Fjarmæling merkir vél sem í gangi þegar
gildið er í eða yfir ON threshold út ON confirm tímann, og sleppir henni aðeins
þegar gildið er í eða undir OFF threshold út OFF confirm tímann. Vél sem dregur
áfram meira en OFF threshold þegar hún er ónotuð — biðljós, dæla eða hitari —
losnar aldrei. Sama gerist ef gildið situr fast á milli þröskuldanna tveggja,
því þar breytist ekkert.

**Tækið hætti að svara.** Misheppnaður lestur merkir vélina offline og þá dettur
hún líka út úr vali. Á spjaldinu birtist strik í stað gildis á meðan Last read
heldur áfram að telja. Það er net- eða tækjavandi, ekki þröskuldavandi.

## Skref {#steps}

1. Opnaðu `/dev/admin`, farðu í Diagnostics og vertu á **Live readings**. Finndu
   vélina sem er röng.
2. Lestu spjaldið að ofan og niður: **Run state**, **Available**,
   **Pending start**, gildið, bandtextann og **Last read**.
3. Ef **Pending start** er já, þá valdi einhver vélina og ræsingin var aldrei
   staðfest. Bíddu eftir að frátekningin renni út og sjáðu hana hreinsast af
   sjálfu sér, lestu svo
   [Vélin fer ekki í gang eftir val](guide:machine-does-not-start).
4. Ef **Run state** er `in_use` á meðan vélin er ónotuð, skoðaðu gildið og
   bandtextann. Gildi sem situr yfir OFF threshold þegar vélin gerir ekkert
   þýðir að þröskuldarnir passa ekki lengur við þessa vél. Skrifaðu niður gildið
   í hvíld og stoppaðu þar. Þröskuldabreytingar eru sérstakt verkferli og blind
   breyting getur tekið vélina úr notkun fyrir alvöru.
5. Ef gildið er strik og **Last read** telur stöðugt upp, þá svarar tækið ekki.
   Athugaðu hvort aðrar vélar á sama tæki eða sama neti eru líka í vandræðum
   áður en þú snertir nokkuð.
6. Ef **Run state** er `available` en skjárinn sýnir vélina samt sem upptekna,
   þá er skjámyndin úrelt frekar en bakendinn. Endurhlaðið skjásíðuna og berðu
   saman aftur.
7. Taktu eftir hvort borðinn um að slökkt sé á fjarmælingu birtist efst í
   Diagnostics. Þegar fjarmæling er slökkt frýs það ástand sem hver vél var í
   þegar lesturinn stöðvaðist.

## Ef þetta lagaði ekki vandann {#escalate}

Láttu vita þegar vélin hefur verið föst lengur en eina frátekningarlotu án þess
að Pending start sé já, þegar gildið uppfærist aldrei, eða þegar ónotuð vél
mælist raunverulega yfir sínum OFF threshold.

Notaðu **Copy support report** neðst í þessari leiðbeiningu og sendu með: hvaða
vél, Run state og gildi eins og þú sást þau, og hvort vélin hafði verið notuð
stuttu áður en hún festist.
