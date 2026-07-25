# Integration and data ownership

Každý bounded context vlastní svá data a význam. Sdílená databáze mezi kontexty je vysoké coupling riziko. Context map musí uvést upstream/downstream, relationship pattern, source of truth, kontrakt, konzistenci, latency a failure handling.

Používej Published Language, Open Host Service nebo ACL tam, kde řeší konkrétní modelovou asymetrii. Event není automaticky integrační kontrakt; musí mít ownera, verzi, idempotency a observability pravidla.
