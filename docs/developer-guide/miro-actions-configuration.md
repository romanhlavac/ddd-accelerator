# Miro Actions configuration

Online Miro acceptance vyžaduje repository-level GitHub Actions konfiguraci s názvem:

```text
MIRO_ACCESS_TOKEN
```

## Nastavení v GitHub webovém rozhraní

1. Otevři repository `romanhlavac/ddd-accelerator`.
2. Zvol `Settings`.
3. Otevři `Security` → `Secrets and variables` → `Actions`.
4. Zůstaň na záložce `Secrets`.
5. V části `Repository secrets` zvol `New repository secret`.
6. Do pole `Name` vlož přesně `MIRO_ACCESS_TOKEN`.
7. Do pole `Secret` vlož pouze přidělenou Miro hodnotu.
8. Nepřidávej prefix `Bearer`, uvozovky ani shell syntaxi.
9. Potvrď `Add secret`.
10. Ověř, že seznam repository secrets obsahuje název `MIRO_ACCESS_TOKEN`. GitHub uloženou hodnotu znovu nezobrazí.

Pro aktuální workflow použij `Repository secret`, nikoli `Variable`, `Codespaces secret`, `Dependabot secret` nebo `Environment secret`.

## Bezpečnost

- Hodnotu nesděluj v chatu nebo PR komentáři.
- Neukládej ji do souboru, shell history nebo Git historie.
- Nepředávej ji jako CLI argument.
- Nevypisuj ji kvůli ověření konfigurace.
- Použij pouze Miro scopes potřebné pro cílový team.

Při podezření na kompromitaci hodnotu revokuj nebo otoč v Miro a repository secret aktualizuj.

## Spuštění online acceptance

Oprávněný actor vloží do PR komentář:

```text
/ddda validate-pr --with-miro --full --keep-review-board
```

Broker ověří policy, same-repository PR, aktuální head SHA a povinné CI checky. Miro konfiguraci zpřístupní pouze odpovídajícímu GitHub Actions kroku.

`--keep-review-board` zachová nový izolovaný acceptance board pro přímou kontrolu a human visual acceptance.

## Ověření výsledku

Zelený workflow `DDDA platform CI` sám o sobě nedokazuje online Miro acceptance. V jobu `Online Miro acceptance` musí tyto kroky skončit `success`:

```text
Check online secret availability
Run exact-SHA online acceptance
Stage online acceptance evidence
Upload online acceptance evidence
```

Když je `Run exact-SHA online acceptance` označen `skipped`, online acceptance neproběhla.

Platná evidence obsahuje aktuální PR head SHA, nový board ID/URL a technický PASS nebo jednoznačný FAIL.

## Troubleshooting

### Online krok je skipped

Zkontroluj přesný název `MIRO_ACCESS_TOKEN`, umístění v `Repository secrets` a repository, ve kterém workflow běží. GitHub Actions neposkytuje repository secrets nedůvěryhodným fork PR.

### Miro vrací 401 nebo 403

Ověř platnost Miro konfigurace, její scopes a přístup k cílovému teamu. Hodnotu případně otoč a repository secret aktualizuj. Nevypisuj ji do logu.

### Workflow je zelený, ale chybí board nebo evidence

Zkontroluj jednotlivé kroky jobu. Bez úspěšného online kroku, board ID/URL a exact-SHA evidence nejde o online acceptance PASS.

### Běh skončil FAIL po vytvoření boardu

Necommituj mapping ani sync state bez výslovného technického PASS. Zachovej board a evidence pro diagnostiku a nespouštěj promotion.

Další provozní a governance pravidla jsou popsána v `remote-validation-broker.md`.
