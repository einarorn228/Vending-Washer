---
id: kiosk-cannot-reach-backend
locale: is
translation_status: review
title: "Skjárinn er úreltur eða nær ekki í bakendann"
summary: "Skjárinn er fastur á einni mynd eða sýnir tengiborða, þótt kerfið sjálft geti verið í lagi."
search_aliases:
  - skjárinn frosinn
  - ekkert samband við bakenda
  - skjárinn uppfærist ekki
  - skjárinn sýnir gamlar upplýsingar
checks:
  - id: kiosk-banner-text
    question: "Er borði á skjánum og hvað stendur á honum?"
    look_for: "Efsti hluti skjásins."
    expected: "Enginn borði. Tengiborði og borði um vantandi API lykil þýða ólíka hluti."
  - id: admin-panel-loads
    question: "Opnast stjórnborðið yfirleitt frá þessari vél?"
    look_for: "Opnaðu /dev/admin í vafra."
    expected: "Það opnast og biður um innskráningu."
    route: overview
    diagnostics: core
  - id: backend-reachable
    question: "Segir Overview að bakendinn náist?"
    look_for: "Overview, Backend reachable."
    expected: "yes."
    route: overview
    diagnostics: core
  - id: state-matches-screen
    question: "Passar ástandið sem bakendinn heldur við það sem skjárinn sýnir?"
    look_for: "Remote Control, ástandsyfirlitið, við hliðina á skjánum sjálfum."
    expected: "Sama ástand. Munur þýðir að skjámyndin er úrelt, ekki bakendinn."
    route: remote_control
    diagnostics: kiosk.state
  - id: screen-follows-after-reload
    question: "Fer skjárinn að fylgjast með aftur eftir að síðan er endurhlaðin?"
    look_for: "Skjárinn í um eina mínútu eftir endurhleðslu."
    expected: "Hann fylgir aftur skönnunum og breytingum á vélum."
---

## Hvenær á að nota þetta {#when-to-use}

Notaðu þessa leiðbeiningu þegar skjárinn fylgir ekki raunveruleikanum: hann
stendur fastur á einni mynd, sýnir upplýsingar sem þú veist að eru úreltar, eða
ber borða um sambandið við bakendann.

Til er stutt útgáfa af þessu fyrir þá sem eru á staðnum án innskráningar, á
opnu hjálparsíðunni. Þessi leiðbeining er greiningarútgáfan og gerir ráð fyrir
að þú getir opnað `/dev/admin` og borið skjáinn saman við það sem bakendinn
heldur í raun.

Farðu varlega í ályktanir af úreltum skjá. Vélarnar á honum geta verið rangar af
tveimur ólíkum ástæðum: skjárinn fær engar uppfærslur, eða mynd bakendans af
vélunum er sjálf stöðnuð. Það síðara er
[Allar vélar sýnast lausar þegar fjarmæling er stöðnuð](guide:all-machines-available-telemetry-stale).

## Mögulegar orsakir {#causes}

**Skjásíðan nær ekki í bakendann.** Skjárinn spyr bakendann um núverandi ástand
á fárra sekúndna fresti — á fresti `kiosk_poll_interval_ms`, sjálfgefið einni
sekúndu. Þegar beiðni mistekst heldur skjárinn síðasta ástandi sem hann fékk og
sýnir borða um að sambandið hafi rofnað. Myndin á skjánum er þá einfaldlega
gömul, ekki röng af ásettu ráði.

**Vafrinn hefur engan API lykil.** Hver beiðni frá skjánum ber API lykil. Ef
vafrinn hefur engan — algengast þegar skjásíðan var endurhlaðin áður en
framendinn var ræstur með lykilinn á sínum stað — sýnir skjárinn borða um það í
stað tengiborðans. Ekkert á skjánum sjálfum lagar það; þetta er verk
umsjónarmanns á sjálfsalavélinni.

**Lykill er til staðar en er ekki samþykktur.** Lykill sem bakendinn hafnar
veldur því að síðan endurhleður sig stuttu eftir hverja tilraun, svo skjárinn
virðist ræsa sig aftur og aftur án þess að setjast.

**Vafrinn skilar svari úr skyndiminni.** Þetta er skráða atvikið á bak við
þessa leiðbeiningu: Chromium hélt í skyndiminnissvar við ástandsbeiðninni og
skjárinn sat á gamalli mynd án nokkurs borða, á meðan bakendinn var heill allan
tímann. Beiðnir eru nú sendar með skyndiminni afvirkt, svo þetta ætti ekki að
endurtaka sig — en úreltur skjár **án** borða er samt myndin sem á að vekja þennan
grun, og endurhleðsla sker úr um það.

**Bakendinn er ekki í gangi.** Þá opnast stjórnborðið ekki heldur og skjárinn
getur ekki jafnað sig af sjálfu sér.

## Skref {#steps}

1. Horfðu á skjáinn og skráðu hvort borði er til staðar og hvað stendur á honum.
   Tengiborðinn og borðinn um vantandi lykil benda á ólíkar orsakir, og enginn
   borði bendir á vafrann frekar en netið.
2. Opnaðu `/dev/admin` frá sjálfsalavélinni eða öðru tæki á sama neti. Ef
   stjórnborðið opnast ekki heldur er þetta ekki skjávandi — láttu vita, því
   bakendinn eða vélin sjálf þarf athygli.
3. Lestu Overview í stjórnborðinu: **Backend reachable** og
   **Current UI state**.
4. Opnaðu Remote Control og berðu ástandið sem það sýnir saman við það sem
   skjárinn sýnir.
   - Þau passa saman: skjárinn er í lagi og bakendinn situr raunverulega í því
     ástandi.
   - Þau passa ekki: skjámyndin er úrelt.
5. Endurhlaðið skjásíðuna og fylgstu með í eina mínútu. Úrelt síða sem fer að
   fylgjast með aftur eftir endurhleðslu var vafravandi, og það er þess virði að
   skrá þótt búið sé að laga orsökina.
6. Ef skjárinn uppfærist en virkar seinn, athugaðu `kiosk_poll_interval_ms` í
   Settings áður en þú gerir ráð fyrir bilun. Langt millibil er stillt val en
   ekki tengivandi.
7. Ekki slá inn eða líma lykla í vafra skjásins til að komast fram hjá borða um
   vantandi lykil. Tilkynntu það í staðinn.

> [!WARNING]
> Úreltur skjár getur sýnt vél lausa þótt hún sé það ekki. Þar til skjárinn
> fylgir bakendanum aftur skaltu ekki láta starfsfólk eða viðskiptavini velja
> vél út frá honum.

## Ef þetta lagaði ekki vandann {#escalate}

Láttu vita þegar stjórnborðið opnast ekki, þegar Overview segir að bakendinn
náist ekki, þegar borðinn um vantandi lykil birtist, eða þegar síðan endurhleður
sig aftur og aftur.

Notaðu **Copy support report** neðst í þessari leiðbeiningu og sendu með:
nákvæman texta borðans, hvort `/dev/admin` opnaðist, hvað Overview sagði um
Backend reachable og Current UI state, og hvort endurhleðsla breytti einhverju.
