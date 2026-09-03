---
id: all-machines-available-telemetry-stale
locale: is
translation_status: review
title: "Allar vélar sýnast lausar þegar fjarmæling er stöðnuð"
summary: "Allar vélar sýnast lausar á skjánum og viðskiptavinum er vísað á vélar sem eru þegar í gangi."
search_aliases:
  - allt sýnist laust
  - mælingar uppfærast ekki
  - viðskiptavinur sendur á vél í gangi
  - framboð rangt á öllum vélum
checks:
  - id: telemetry-setting-on
    question: "Er kveikt á fjarmælingu í Settings?"
    look_for: "Settings, hópurinn Shelly / Runtime Toggles, Telemetry polling enabled."
    expected: "Kveikt. Slökkt skýrir að allar vélar sýnast lausar."
    route: settings
    diagnostics: settings.telemetry
  - id: telemetry-off-banner
    question: "Birtir Diagnostics viðvörunarborða um að slökkt sé á fjarmælingu?"
    look_for: "Rauði borðinn efst á Diagnostics flipanum."
    expected: "Enginn borði þegar lestur er í gangi."
    route: diagnostics
    diagnostics: settings.telemetry
  - id: last-read-age
    question: "Telur Last read stöðugt upp á öllum vélum?"
    look_for: "Diagnostics, Live readings, Last read á hverju spjaldi."
    expected: "Lág tala sem núllstillist, um það bil poll interval vélarinnar."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: values-frozen
    question: "Breytast gildin yfirleitt á meðan vél er örugglega í gangi?"
    look_for: "Diagnostics, Live readings, gildið og línuritið fyrir vél í gangi."
    expected: "Gildið hreyfist. Gildi sem er frosið á sömu tölu er einkennið."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: run-state-all-available
    question: "Sýna allar vélar run state available, líka sú sem þú heyrir í?"
    look_for: "Diagnostics, Live readings, Run state á öllum spjöldum."
    expected: "Vél í gangi á að sýna in_use."
    route: diagnostics
    diagnostics: machine.identity
---

## Hvenær á að nota þetta {#when-to-use}

Notaðu þessa leiðbeiningu þegar skjárinn sýnir **allar** vélar lausar, líka
vélar sem sjást eða heyrast í gangi, og viðskiptavinir borga fyrir vél sem er
þegar í notkun.

Þetta er dýrari bilunin af framboðsvandamálunum tveimur, því notkun
viðskiptavinarins er eydd áður en nokkur tekur eftir. Ef aðeins **ein** vél er
röng, og hún er föst á hinn veginn — sýnir sig upptekna þótt hún sé laus —
lestu þá [Vélin sýnist upptekin þótt hún sé laus](guide:machine-unavailable).

## Mögulegar orsakir {#causes}

Vélar skipta aðeins um ástand af því að fjarmæling les þær. Þegar lesturinn
stöðvast heldur hver vél því ástandi sem hún var í á þeirri stundu, og bakendi
sem var nýlega ræstur heldur öllum vélum sem lausum. Þess vegna er "allt er
laust" nánast alltaf merki um að **ekkert sé lesið**, ekki um bilað tæki. Tæki
sem hættir að svara eitt og sér er merkt offline og dettur þá út úr vali.

**Slökkt er á fjarmælingu.** Þegar `telemetry_enabled` er slökkt heldur lestrarlykkjan
áfram að ganga en les ekkert. Diagnostics segir það beint með rauðum borða og
gildin standa kyrr.

**Bakendinn sem keyrir er ekki sá sem þú stilltir.** Þetta er skráða atvikið úr
rekstri: slökkt hafði verið á fjarmælingu og ferlið sem var í gangi tók ekki
heldur við breytingunni, svo allar vélar sýndust lausar heilt síðdegi. Merkið
sem þú sérð er það sama í báðum tilvikum — **Last read** telur upp á öllum
spjöldum á meðan gildin standa frosin.

**Ekkert hefur nokkurn tíma verið lesið.** Á bakenda þar sem lestur hefur aldrei
farið í gang birtast strik í stað frosinna talna, og Last read sýnir líka strik.

## Skref {#steps}

1. Opnaðu `/dev/admin`, farðu í Diagnostics og vertu á **Live readings**.
   Skoðaðu efsta hluta flipans fyrst. Rauður borði um slökkta fjarmælingu svarar
   spurningunni einn og sér.
2. Horfðu á spjöldin í um tíu sekúndur. Taktu eftir hvort **Last read**
   núllstillist niður í lága tölu eða telur stöðugt upp á öllum vélum í einu.
3. Finndu vél sem þú veist að er í gangi og berðu gildið og bandtextann saman
   við það sem þú heyrir. Vél í gangi sem sýnir sömu tölu og ónotuð vél er ekki
   lesin.
4. Farðu í Settings, opnaðu hópinn **Shelly / Runtime Toggles**, og athugaðu
   **Telemetry polling enabled** (`telemetry_enabled`). Ef slökkt er á því er lausnin að kveikja á því. Það
   tekur gildi án endurræsingar. Breyttu aðeins þessari einu stillingu.
5. Farðu aftur í Diagnostics og staðfestu bata: **Last read** á að detta niður í
   lága tölu, gildin eiga að fara á hreyfingu og vél í gangi á að skipta yfir í
   `in_use` eftir sinn ON confirm tíma.
6. Ef þegar var kveikt á stillingunni og gildin standa samt frosin, þá er
   bakendinn sem keyrir ekki að taka við stillingunum. Skrifaðu það niður og
   stoppaðu. Endurræsing bakendans á sjálfsalavélinni er verk umsjónarmanns og
   stjórnborðið sýnir nákvæmu skipunina í endurræsingarborðanum þegar hennar er
   þörf.
7. Þangað til framboðið er aftur áreiðanlegt skaltu segja starfsfólki að treysta
   ekki skjánum um hvaða vélar séu lausar.

> [!WARNING]
> Á meðan fjarmæling er stöðnuð getur skjárinn ekki greint upptekna vél frá
> lausri. Meðhöndlaðu allar vélar sem óvissar þar til Last read er aftur lág
> tala á öllum spjöldum.

## Ef þetta lagaði ekki vandann {#escalate}

Láttu strax vita ef viðskiptavinum er enn vísað á vélar í gangi eftir að
staðfest er að kveikt sé á fjarmælingu, eða ef gildin standa áfram frosin.

Notaðu **Copy support report** neðst í þessari leiðbeiningu og sendu með: hversu
margar vélar eru rangar, Last read gildin sem þú sást, hvort borðinn um
fjarmælingu birtist, og um það bil hvenær fyrsta kvörtunin barst.
