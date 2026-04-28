# ModelPrinter

Webapp interna per Canon imagePROGRAF TC-20 a rullo 24″ / 610 mm.

Flusso:

1. trascini un PDF nella pagina;
2. il backend porta a minimo `1` gli spessori vettoriali PDF sotto soglia;
3. la pagina mostra il PDF modificato in preview;
4. clic su **Stampa** invia il PDF a CUPS.

## Sviluppo locale

```bash
poetry install
MODELPRINTER_JOB_ROOT=./data/jobs poetry run flask --app modelprinter.app:app run --debug
```

## Variabili

- `MODELPRINTER_JOB_ROOT`: directory job PDF, default `/var/lib/modelprinter/jobs`
- `MODELPRINTER_MIN_STROKE_WIDTH`: default `1`
- `MODELPRINTER_CUPS_PRINTER`: default `Canon_TC_20`
- `MODELPRINTER_CUPS_OPTIONS`: default `InputSlot=MainRoll,CutMedia=Auto,sides=one-sided`
- `MODELPRINTER_MAX_UPLOAD_MB`: default `80`

## Canon TC-20 / rullo 24″

La TC-20 è una plotter Canon imagePROGRAF da 24″, quindi rullo circa 610 mm. Se possibile usare IPP Everywhere/driverless via CUPS. La stampante viene vista in LAN come servizio Bonjour/IPP `Canon TC-20`.
