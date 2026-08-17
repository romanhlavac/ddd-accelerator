# Architecture styles and trade-offs

Nezačínej stylem architektury. Nejprve ověř doménové hranice, tok změn, data ownership, konzistenci a provozní požadavky. Modulární monolit je legitimní výchozí volba; mikroservisy vyžadují nezávislé ownership a deployment hranice.

Event-driven, hexagonal, microservices, CQRS nebo serverless hodnotit podle konkrétních drivers. U každé varianty uvést failure modes, observability, testovatelnost, provozní náklady a migrační cestu.
