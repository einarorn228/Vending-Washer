---
id: machine-does-not-start
locale: is
translation_status: review
title: "Vélin fer ekki í gang eftir val"
summary: "Kóðinn var samþykktur og vél valin, en vélin fer aldrei í gang."
search_aliases:
  - vélin fer ekki í gang
  - ekkert gerist eftir að vél er valin
  - vélin fær ekki straum
  - ræsing virkar ekki
checks:
  - id: program-selected
    question: "Var prógramm valið á vélinni sjálfri eftir að hún var valin á skjánum?"
    look_for: "Stillihnappar vélarinnar sjálfrar, ekki skjár sjálfsalans."
    expected: "Vélin fer ekki í gang fyrr en prógramm er valið á henni."
  - id: kiosk-message
    question: "Hvað birtist á skjánum strax eftir að vélin var valin?"
    look_for: "Overview, Current UI state, á meðan þú endurtekur tilraunina."
    expected: "Skilaboð sem nefna vélina. Machine start failed þýðir að skipunin komst ekki alla leið."
    route: overview
    diagnostics: kiosk.state
  - id: relay-control-enabled
    question: "Er relay-stýring bakendans virk?"
    look_for: "Overview, Backend relay."
    expected: "Enabled. Þegar hún er slökkt sendir bakendinn aldrei straumskipun á neina vél."
    route: overview
    diagnostics: settings.relay
  - id: pending-start-held
    question: "Heldur vélin enn frátekningu eftir valið?"
    look_for: "Diagnostics, Live readings, Pending start fyrir vélina."
    expected: "Já rétt eftir tilraun, svo nei þegar frátekningin rennur út."
    route: diagnostics
    diagnostics: machine.identity
  - id: reading-responds
    question: "Hreyfist mælingin þegar vélin er ræst?"
    look_for: "Diagnostics, Live readings, gildið og Last read fyrir vélina."
    expected: "Gildið hækkar innan fárra sekúndna ef vélin fer raunverulega í gang."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: reading-reaches-on-threshold
    question: "Nær mælingin ON threshold og helst þar?"
    look_for: "Diagnostics, Live readings, bandtextinn og Above for borið saman við ON confirm."
    expected: "at or above ON threshold, haldið að minnsta kosti jafn lengi og ON confirm."
    route: diagnostics
    diagnostics: machine.thresholds
---

## Hvenær á að nota þetta {#when-to-use}

Notaðu þessa leiðbeiningu þegar skönnun var samþykkt, viðskiptavinurinn valdi
vél á skjánum, skjárinn svaraði með skilaboðum sem nefna vélina, en vélin fer
samt aldrei í gang. Nokkrum sekúndum síðar fer skjárinn sjálfkrafa aftur á
byrjunarskjáinn.

Ef viðskiptavinurinn gat alls ekki valið vélina, af því að hún sýndi *In use*,
átt þú við annað vandamál. Lestu þá
[Vélin sýnist upptekin þótt hún sé laus](guide:machine-unavailable).

Eitt getur þú sagt viðskiptavininum strax: notkun er aðeins dregin frá þegar
bakendinn sér vélina fara raunverulega í gang. Val sem varð aldrei að þvotti
eyðir engri notkun, svo það má skanna sama kóða aftur.

## Mögulegar orsakir {#causes}

**Slökkt er á relay-stýringu.** Bakendinn sendir aðeins straumskipun þegar
`backend_relay_enabled` er kveikt. Þegar slökkt er á því sýnir skjárinn samt
venjuleg skilaboð og tekur vélina frá, en ekkert er sent á vélbúnaðinn. Þetta er
prufustillingin sem notuð er á vinnuborði og hún er algengasta ástæðan fyrir því
að val virðist samþykkt en ekkert gerist.

**Straumskipunin komst ekki á leiðarenda.** Þegar kveikt er á relay-stýringu
biður bakendinn Shelly-tæki vélarinnar um að loka rásinni og reynir einu sinni
aftur. Ef tækið svarar ekki innan `shelly_http_timeout_sec` er frátekningin
losuð strax og skjárinn sýnir *Machine start failed*. Það bendir á tækið eða
netið, ekki á skjáinn.

**Vélin fékk straum en ekkert prógramm var valið á henni.** Skilaboðin biðja
viðskiptavininn um að velja prógramm á vélinni sjálfri. Þangað til dregur vélin
nánast ekkert og virðist óvirk í augum bakendans.

**Ræsingin var aldrei staðfest.** Skjárinn kemst aðeins á staðfestingarskjáinn
þegar fjarmæling sér gildi vélarinnar í eða yfir ON threshold og heldur því þar
út ON confirm tímann. Ef gildið nær aldrei svo hátt, eða dettur of fljótt niður
aftur, berst engin staðfesting. Skjárinn núllstillist eftir
`selection_notice_seconds` og vélin helst frátekin þar til
`machine_reservation_minutes` rennur út.

**Slökkt er á fjarmælingu.** Þegar `telemetry_enabled` er slökkt les ekkert
vélarnar og því er ekki hægt að staðfesta neina ræsingu. Sjá
[Allar vélar sýnast lausar þegar fjarmæling er stöðnuð](guide:all-machines-available-telemetry-stale).

## Skref {#steps}

1. Fylgstu með einni tilraun frá byrjun til enda og skrifaðu niður
   nákvæmlega hvað skjárinn sýndi eftir að vélin var valin. *Machine start
   failed* og venjuleg ræsiskilaboð leiða til gjörólíkra orsaka.
2. Opnaðu `/dev/admin` og lestu Overview. Taktu eftir **Backend relay** og
   **Telemetry**. Ef Backend relay er slökkt sendir bakendinn engar
   straumskipanir — stoppaðu þar og láttu vita í stað þess að kveikja á henni,
   því sú stilling lætur bakendann stýra raunverulegum vélbúnaði.
3. Farðu í Diagnostics, Live readings, og finndu vélina. Taktu eftir
   **Run state**, **Pending start**, **Last read**, gildinu og bandtextanum.
4. Endurtaktu eina ræsitilraun og horfðu á spjaldið á meðan. Vél sem fær
   raunverulega straum sýnir gildi sem hækkar innan fárra sekúndna.
5. Ef gildið hækkar en bandtextinn segir aldrei *at or above ON threshold*, eða
   **Above for** nær aldrei ON confirm tímanum, þá er vélin í gangi en ekki hægt
   að staðfesta það. Ekki breyta þröskuldum í miðju útkalli. Þröskuldastilling
   er sérstakt verkferli og röng breyting getur gert framboðið verra.
6. Opnaðu Diagnostics, Change history, og leitaðu að nýlegri breytingu á
   runtime- eða vélbúnaðarstillingu. Ræsivandi sem byrjaði í dag byrjaði
   yfirleitt með breytingu í dag.
7. Bíddu eftir að frátekningin renni út áður en þú prófar aftur. Vél sem heldur
   enn frátekningu er ekki hægt að velja á ný.

## Ef þetta lagaði ekki vandann {#escalate}

Láttu vita þegar slökkt er á relay-stýringu og það er ekki þín ákvörðun að
kveikja á henni, þegar mælingin hreyfist alls ekki, eða þegar skjárinn sýnir
*Machine start failed* aftur og aftur.

Notaðu **Copy support report** neðst í þessari leiðbeiningu og sendu með: hvaða
vél, nákvæman texta skjásins, hversu margar sekúndur liðu þar til skjárinn
núllstilltist, og hvort mælingin hreyfðist yfirleitt.
