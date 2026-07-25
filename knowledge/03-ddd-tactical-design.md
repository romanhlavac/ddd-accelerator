# Tactical DDD

Taktický návrh používej až uvnitř dostatečně vymezeného bounded contextu. Agregát je consistency boundary chránící invarianty, ne kolekce tabulek. Zapisuj command, invariant, state transition, domain event a failure semantics.

Preferuj jednoduchý model. CQRS, Event Sourcing a distribuované transakce vyžadují explicitní business nebo quality-attribute zdůvodnění. U externích produktů modeluj vlastní odpovědnost, integrační hranici a ACL; nevymýšlej interní doménový model dodavatele bez evidence.
