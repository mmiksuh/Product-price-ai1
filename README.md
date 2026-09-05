# Product Price AI

MVP, joka:
1. vastaanottaa 1–5 tuotekuvaa
2. tunnistaa tuotteen
3. tekee verkkopohjaisen hintatutkimuksen
4. arvioi arvon ja suositellun pyyntihinnan
5. laskee voiton/ROI:n
6. vie tulokset Exceliin

## Käynnistys

```bash
pip install -r requirements.txt
streamlit run app.py
```

Anna OpenAI API-avain sivupalkissa.

Huom: MVP on tarkoitettu prototyypiksi. Hintalähteiden käyttöehdot, markkinapaikkojen API:t,
valuutat, toimituskulut ja toteutuneiden myyntien saatavuus kannattaa ratkaista erikseen
ennen kaupallista käyttöä.
