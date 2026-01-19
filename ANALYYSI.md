# Tekoälyn käyttö projektissa

## 1. Mitä tekoäly teki hyvin?

Tekoäly ymmärsi mielestäni tosi hyvin ensimmäisen promptin joka oli myös pääprompti ja se toimi sen mukaan. Tekoäly tuotti omasta mielestäni selkeää ja helposti luettavaa koodia. Koodin struktuuri oli looginen ja pyytämäni kommentit koodiin auttoivat minua ymmärtään helpommin koodia. Mielestäni tekoäly ei tuottanut mitään ylimääräistä koodia. Tekioälyn avulla säästin myös aikaa ohjelman testaamisessa sillä sain komennot siltä jotka pystyin sitten helposti kopioimaan omaan terminaaliini jossa testasin kaikki mahdollliset toiminnot.

## 2. Mitä tekoäly teki huonosti?

Tekoäly ei toiminut omasta mielestäni huonosti sillä osasin prompatata ja saada tarvittavat tiedot ulos siltä. Jos jotain voisin mainita niin tekoälyn generoimat kommentit olivat hieman epäselviä ja vaikeasti ymmärrettäviä. Lopputuloksessa kommentteja oli liikaa vaikka itse promptasinkin "comment each line", mutta tämä teki kuitenki koodin ymmärtämisestä helpomman ennenkuin aloin itse muuttamaan kommentteja.

## 3. Mitkä olivat tärkeimmät parannukset, jotka teit tekoälyn tuottamaan koodiin ja miksi?

Kommentien selkeys ja niiden ryhmittely jotta koodi olisi helpommin ymmärrettävissä ja kevyempi koodin rakenne.

Testauksien jälkeen lisäsin uuden toiminnalisuuden joka rajaa huoneiden varausten vain meneillään olevan vuoden aikana. Eli käyttäjä ei pysty varaamaan huoneita vuosien päähän. Tämä vähentää myös käyttäjien virheitä kuten esimerkiksi valita jokin kaukainen vuosi. Tämä oli oma oletus ja mielestäni looginen käytäntö että varauksia tehdään yleensä lähiajalle. Tähän liittyen testauksien yhteydessä sain seuraavan errorin `"500 Internal Server Error"`, koska API-endpointin create reservation sisällä heitettiin `ValueError`-poikkeus. Jotta virhe palautuisi oikein asiakkaalle niin lisäsin `HTTPExeption`in, jossa on määritelty HTTP-statuskoodi ja virheviesti toiminnan selkeyttämiseksi. Error tuli kuitenkin oikeassa kohdassa testauksessa niin sen olisi pitänyt palauttaa teksti `"Reservations must be within the current year (2026)"` eikä internal server error. Tämän korjasin.

## Omat oletukset tehtävään

- Huoneita on 6  
- Huoneen nimet: Aurora, Borealis, Helmi, Sauna, Sisu, Taiga
- Varauksia voi suodattaa käyttäjän perustella. Esim voi nähdä kuka on varannut tietyn huoneen. 
- Ajat validoidaan niiden mukana annetun aikavyöhykkeen perusteella, jotta eri maista tehtyjä varauksia voidaan tukea. Tarkistin että Vincitillä on toimipisteitä myös ulkomailla.  
- Varauksia voi tehdä vain meneillään olevan vuoden aikana.

## Omat pohdinnat

Mielestäni tehtävä oli erittäin mielenkiintoinen projekti ja todisti sen, että nykypäivänä tekoälystä on suuri apu ohjelmoinnissa ja dokumentoinnissa. Tässä projektissa tekoäly teki suurimman osan koodista ja minulle jäi testausten iterointi, validointi ja pienien muutoksien tekeminen.
