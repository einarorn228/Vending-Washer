---
id: scanner-not-scanning
locale: is
translation_status: review
title: "Skannarinn les ekki"
summary: "Kóði er settur undir skannarann og ekkert gerist á skjánum."
search_aliases:
  - skannarinn gerir ekkert
  - qr kóði les ekki
  - engin viðbrögð við skönnun
  - ljósið á skannaranum er slökkt
checks:
  - id: scanner-reacts
    question: "Bregst skannarinn sjálfur við þegar kóði er settur undir hann?"
    look_for: "Ljósið og hljóðið í skannaranum sjálfum, ekki skjárinn."
    expected: "Hann kviknar og pípir við hvern kóða."
  - id: scanner-available
    question: "Hefur bakendinn skannarann opinn?"
    look_for: "Overview, Scanner available."
    expected: "yes. no þýðir að ekki tókst að opna raðtengið þegar bakendinn ræsti."
    route: overview
    diagnostics: scanner.status
  - id: scanner-port
    question: "Er stillt raðtengi það sama og skannarinn er tengdur við?"
    look_for: "Overview, Scanner port."
    expected: "Tengið sem skannarinn birtist á í þessari vél, venjulega /dev/ttyACM0."
    route: overview
    diagnostics: scanner.status
  - id: scan-log-row
    question: "Birtist ný lína í skönnunarskránni þegar þú skannar?"
    look_for: "Diagnostics, Scan log, nýjasta línan og Details dálkurinn."
    expected: "Engin ný lína þýðir að skönnunin komst aldrei inn í ferlið."
    route: diagnostics
    problem_guide: code-rejected
  - id: recent-scanner-setting-change
    question: "Var skannarastillingum breytt án þess að endurræsa á eftir?"
    look_for: "Diagnostics, Change history, og endurræsingarborðinn efst í stjórnborðinu."
    expected: "Engin óafgreidd breyting. Vistaðar skannarastillingar taka aðeins gildi eftir endurræsingu."
    route: diagnostics
    diagnostics: settings.scanner
---

## Hvenær á að nota þetta {#when-to-use}

Notaðu þessa leiðbeiningu þegar viðskiptavinur setur kóða undir skannarann og
**ekkert gerist**: enginn valskjár, engin villa, engin skilaboð.

Ef skjárinn bregst við en sýnir rauða villu og fer aftur á byrjunarskjáinn, þá
komst skönnunin inn og var hafnað. Lestu þá
[Kóða er hafnað eða skönnun kemst ekki áfram](guide:code-rejected). Þessi
munur er fljótlegasta skiptingin á öllu þessu svæði: þögn bendir á skannarann,
villa bendir á kóðann.

## Mögulegar orsakir {#causes}

**Bakendinn opnaði aldrei skannarann.** Raðtengið er opnað einu sinni þegar
bakendinn ræsir. Ef skannarinn var ótengdur á þeirri stundu, eða stillta tengið
var rangt, fer lestrarþráðurinn aldrei í gang og engin skönnun kemst inn fyrr en
bakendinn er endurræstur. Overview segir þetta beint með *Scanner available: no*.

**Skannarastillingum var breytt en þær voru ekki teknar í notkun.**
`serial_port`, `serial_baudrate` og `scan_timeout` eru lesin aðeins þegar
skannarinn er opnaður. Að vista þau breytir geymda gildinu en ekki skannaranum
sem er í gangi, og þess vegna merkir stjórnborðið þau sem endurræsingarstillingar.

**Kóðinn er ekki af því formi sem kerfið tekur við.** Bakendinn sendir aðeins
áfram strengi sem líta út eins og heimild: átta stafa kóða, UUID, 32 stafa
hex-streng eða PIN með fjórum til tólf tölustöfum. Allt annað — vörustrikamerki,
vildarkort, rifinn eða illa prentaður miði — er hunsað án skilaboða og án línu í
skönnunarskránni.

**Skannarinn sjálfur les ekki.** Ef skannarinn kviknar ekki og pípir ekki er
vandinn framar en hugbúnaðurinn: straumur, snúra eða stillingar skannarans
sjálfs.

## Skref {#steps}

1. Settu kóða undir skannarann og horfðu á skannarann, ekki á skjáinn. Skannari
   sem kviknar ekki og pípir ekki les ekkert, og engin stilling í stjórnborðinu
   breytir því.
2. Opnaðu `/dev/admin` og lestu Overview: **Scanner available** og
   **Scanner port**. Ef Scanner available er *no* hefur bakendinn engan skannara
   opinn og allar skannanir verða þöglar þar til það er lagað.
3. Farðu í Diagnostics, **Scan log**, og skannaðu aftur með skjáinn á
   byrjunarskjánum. Fylgstu með hvort ný lína birtist.
   - Ný lína þýðir að skannarinn virkar og vandinn liggur í kóðanum sjálfum.
   - Engin lína þýðir að ekkert komst inn í ferlið.
4. Prófaðu kóða sem þú veist að er í lagi, til dæmis einn sem þú skannaðir
   nýlega með góðum árangri. Ef hann les og kóði viðskiptavinarins ekki, þá er
   miðinn vandinn en ekki skjárinn.
5. Skoðaðu Diagnostics, **Change history**, fyrir nýlegri breytingu á
   skannarastillingu og athugaðu hvort endurræsingarborðinn er efst í
   stjórnborðinu. Vistaðar skannarastillingar taka fyrst gildi þegar bakendinn
   hefur verið endurræstur á sjálfsalavélinni, og borðinn sýnir þeim sem gerir
   það nákvæmu skipunina.
6. Ekki breyta `serial_port` eða `serial_baudrate` til að sjá hvað gerist. Rangt
   tengi skilur skjáinn eftir með engan skannara eftir næstu endurræsingu, sem er
   verri bilun en sú sem þú byrjaðir með.

## Ef þetta lagaði ekki vandann {#escalate}

Láttu vita þegar Scanner available er *no*, þegar skannarinn bregst ekki við
líkamlega, eða þegar skönnunarskráin er tóm þótt skannarinn pípi eðlilega.

Notaðu **Copy support report** neðst í þessari leiðbeiningu og sendu með: hvað
skannarinn gerði líkamlega, hvað Overview sýndi fyrir Scanner available og
Scanner port, hvort einhver lína birtist í skönnunarskránni, og hvort einn
tiltekinn kóði eða allir kóðar eru undir.
