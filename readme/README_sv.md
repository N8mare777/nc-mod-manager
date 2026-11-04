# NightCoop Manager 0.2.1

## Vad är det

Ett litet verktyg för att installera, uppdatera och ta bort modden **NightCoop** för
**Cyberpunk 2077**. Det är en enda EXE-fil — inget annat behöver installeras.

Programmet är helt portabelt: det **sparar inga inställningar** — varken i registret eller i
egna filer. Ladda ner, installera modden, ta bort programmet. Inget lämnas kvar.

## Funktioner

- Automatisk sökning efter spelkatalogen: Steam (register och bibliotek), GOG (register),
  Epic Games (launcher-manifest) samt vanliga standardkataloger. Varje kandidat verifieras
  med att `bin\x64\Cyberpunk2077.exe` finns
- Manuellt val av mapp om spelet ligger på ett ovanligt ställe
- Val av spelversion (2.5 / 2.31) och modversion
- Installera / uppdatera / avinstallera modden
- Kontroll av tillgänglig version online
- Backup av moddens inställningar (`install-id.txt`, `name.txt`, `servers.txt`)
- "Vad är nytt" för vald build
- Spara sessionsloggen till fil (knapp)
- Tre gränssnittsspråk: svenska, engelska, ryska

## Hur det fungerar

1. Programmet läser `releases.json` från `nightcoop.net` och väljer den build som matchar
   vald spelversion (2.5 eller 2.31). Filer utan spelversionsbegränsning räknas som
   kompatibla med alla versioner.
2. Det laddar ner arkivet för vald build och kontrollerar SHA-256.
3. Det packar upp arkivet och kopierar filerna till spelkatalogen.
4. Det skriver den installerade versionen till `red4ext\plugins\NightCoop\version.txt` och
   skapar ett installationsmanifest `.nightcoop-manifest.json` med alla filer och hashvärden.

Vid uppdatering rensas först moddens mapp `red4ext\plugins\NightCoop\` från föregående
versions filer så att inga gamla DLL:er ligger kvar. `install-id.txt`, `name.txt`,
`servers.txt`, loggfiler och `backup-*`-mappar rörs aldrig.

**Avinstallera** använder manifestet: bara filer som programmet själv installerade tas bort,
och bara om de inte ändrats av något annat. Filer som fanns före installationen återställs
från en säkerhetskopia. Spelfiler, andra moddar och dina sparade spel rörs aldrig.

## Viktigt: gör backup före uppdatering

Mappen `red4ext\plugins\NightCoop\` innehåller viktiga data: `install-id.txt`, `name.txt`,
`servers.txt` och loggfiler. Där finns installations-ID och serverlistan — alltså din
progress och bindning.

Tryck på **Säkerhetskopiera** före uppdatering eller borttagning: programmet skapar mappen
`backup-DATUM-TID` och kopierar filerna dit så att inget går förlorat.

Uppdatering och avinstallation tar inte bort dessa filer, men backup rekommenderas ändå
som en säkerhet.

## Logg

Programmet för en sessionslogg i temp-mappen `%TEMP%\NightCoopManager\`.
Knappen **Spara logg** låter dig spara den var du vill — till exempel för att bifoga
till en felrapport.

## Rekommendationer

- Stäng spelet före installation eller uppdatering.
- Använd samma modbuild som dina vänner — co-op kräver samma version hos alla.
- Om modden inte startar, kontrollera att Red4ext finns (det ingår redan i NightCoop-arkivet).

## Ansvarsfriskrivning

Författaren till detta program har **ingen koppling** till författarna av NightCoop-modden.
Programmet skrevs för att göra installation och uppdatering enklare; det laddar bara ner det
officiella arkivet från `nightcoop.net` och kopierar filerna till spelkatalogen.

Vid problem med själva modden — den startar inte, kraschar, kan inte ansluta till servrar,
frågor om gameplay eller bannlysningar — kontakta **moddens skapare och webbplatsen
nightcoop.net**, inte författaren till detta program.

## Version

0.2.1
