---
id: code-rejected
locale: is
translation_status: review
title: "Kóða er hafnað eða skönnun kemst ekki áfram"
summary: "Skjárinn bregst við skönnuninni með villu og fer aftur á byrjunarskjáinn."
search_aliases:
  - kóði útrunninn eða ógildur
  - kóðinn virkar ekki
  - qr kóða hafnað
  - kerfið er upptekið
  - engin notkun eftir
checks:
  - id: error-message-shown
    question: "Sýndi skjárinn villu, eða gerðist alls ekkert?"
    look_for: "Skjárinn á meðan skannað er."
    expected: "Villuskilaboð. Alger þögn er skannaravandi, ekki kóðavandi."
    problem_guide: scanner-not-scanning
  - id: scan-log-row
    question: "Hvað segir skönnunarskráin um þessa skönnun?"
    look_for: "Diagnostics, Scan log, nýjasta línan, Result og Details."
    expected: "Lína með result invalid og details sem nefnir ástæðuna."
    route: diagnostics
  - id: kiosk-was-ready
    question: "Var skjárinn á byrjunarskjánum þegar kóðinn var skannaður?"
    look_for: "Overview, Current UI state, og textinn á skjánum."
    expected: "waiting_for_code. Skönnunum í öðru ástandi er hafnað sem uppteknum."
    route: overview
    diagnostics: kiosk.state
  - id: active-provider
    question: "Hvaða þjónustuveita staðfestir kóða núna?"
    look_for: "Overview, Provider og Reisa enabled."
    expected: "Sú veita sem á við á þessum stað."
    route: overview
    diagnostics: settings.provider
  - id: another-code-works
    question: "Virkar annar kóði á sama skjá?"
    look_for: "Skjárinn eftir að annar kóði, sem þú veist að er í lagi, er skannaður."
    expected: "Hann fer áfram í vélaval, sem þrengir vandann að fyrri kóðanum."
---

## Hvenær á að nota þetta {#when-to-use}

Notaðu þessa leiðbeiningu þegar skjárinn bregst greinilega við skönnun — stutt
villuskilaboð birtast og skjárinn fer aftur á byrjunarskjáinn eftir nokkrar
sekúndur — en viðskiptavinurinn kemst aldrei í vélaval.

Ef alls ekkert gerist við skönnun er þetta röng leiðbeining. Lestu þá
[Skannarinn les ekki](guide:scanner-not-scanning).

Textinn á skjánum er það gagnlegasta sem þú getur skrifað niður. *Code expired
or invalid*, *No remaining uses*, *Missing code* og *System busy* koma frá
fjórum ólíkum stöðum í ferlinu.

## Mögulegar orsakir {#causes}

**Kóðinn er fullnýttur eða útrunninn.** Í staðbundnum kóðum er kóða hafnað
þegar notkunin er uppurin eða gildistíminn liðinn. Síðasta notkunin setur líka
gildistíma einn dag fram í tímann, svo fullnýttur kóði helst hafnaður eftir það.
`code_expiration_days` hefur aðeins áhrif á kóða sem búnir eru til eftir
breytinguna, svo hún skýrir aldrei gamlan kóða sem hætti að virka í dag.

**Heimildin á enga notkun eftir.** Þegar Reisa er virka þjónustuveitan hafnar
skjárinn skönnun þar sem eftirstæð notkun er komin í núll, með skilaboðum um
það. Þetta er eðlileg niðurstaða fyrir kóða sem hefur þegar verið notaður eins
oft og greitt var fyrir.

**Skjárinn var ekki tilbúinn.** Skannanir eru aðeins samþykktar á
byrjunarskjánum. Skönnun sem berst á meðan fyrri viðskiptavinur er enn að velja
vél, eða á meðan villa er sýnd, er hafnað sem upptekinni og skráð með þeirri
ástæðu. Tveir sem skanna með fárra sekúndna millibili framkalla þetta örugglega.

**Ekki náðist í þjónustuveituna eða hún hafnaði uppflettingu.** Í Reisa-ham
spyr skjárinn veituna um hverja skönnun. Netvandi, tímamörk eða höfnuð beiðni
birtast öll sem villa á skjánum og misheppnuð uppfletting í skönnunarskránni.

**Röng þjónustuveita er virk.** Kóðar eru staðfestir staðbundið nema
`provider_default` sé Reisa **og** kveikt sé á `provider_reisa_enabled`. Ef
staðurinn selur Reisa-heimildir en skjárinn staðfestir staðbundið, þá þekkir
hann engan raunverulegan kóða og hafnar hverri skönnun.

## Skref {#steps}

1. Skrifaðu niður nákvæm skilaboð skjásins og um það bil hvenær þau birtust.
2. Opnaðu `/dev/admin`, farðu í Diagnostics, **Scan log**, og finndu skönnunina.
   **Details** dálkurinn geymir ástæðuna sem bakendinn skráði — upptekið ástand,
   ógildan eða útrunninn kóða, eða misheppnaða uppflettingu hjá veitunni.
3. Lestu Overview: **Provider** og **Reisa enabled**. Berðu saman við það sem
   þessi staður á að selja. Ósamræmi þar skýrir að allir kóðar bregðist í einu.
4. Ef ástæðan segir að skjárinn hafi verið upptekinn, fylgstu með skjánum
   stutta stund. Lausnin er tímasetning en ekki kóðinn: leyfðu skjánum að fara
   aftur á byrjunarskjáinn áður en skannað er. Skjár sem fer aldrei aftur á
   byrjunarskjáinn er annað vandamál — sjá
   [Vélin fer ekki í gang eftir val](guide:machine-does-not-start).
5. Skannaðu annan kóða sem þú veist að er í lagi. Einn kóði sem bregst á meðan
   aðrir virka er spurning um heimild viðskiptavinarins, ekki bilun í skjánum.
6. Ef allir kóðar bregðast og veitan er Reisa, meðhöndlaðu það sem
   veitu- eða netatvik frekar en kóðaatvik og láttu vita. Reisa-stillingar eru
   áhættusamar og hvorki grunnslóðin né lykillinn eru til að prófa sig áfram með
   í miðri þjónustu.

> [!NOTE]
> Stjórnborðið og stuðningsskýrslan skrá aðeins **hvort** Reisa-slóð og lykill
> séu stillt, aldrei gildin sjálf. Ekki lesa upp eða senda lykil þegar þú
> tilkynnir þetta vandamál.

## Ef þetta lagaði ekki vandann {#escalate}

Láttu vita þegar öllum kóðum er hafnað, þegar skönnunarskráin sýnir misheppnaðar
uppflettingar hjá veitunni, eða þegar viðskiptavinur fullyrðir að ónotaðir
þvottar séu eftir á kóðanum.

Notaðu **Copy support report** neðst í þessari leiðbeiningu og sendu með:
nákvæm skilaboð skjásins, Details gildið úr skönnunarskránni, hvort einn kóði
eða allir kóðar eru undir, og hvaða veitu Overview sýndi.
