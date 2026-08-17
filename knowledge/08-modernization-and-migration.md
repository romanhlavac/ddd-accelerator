# Modernization and migration

Odděl business realitu od současné implementace. Nejprve zmapuj pain, skrytá pravidla, data ownership, runtime a change coupling, system of record a provozní rizika.

Preferuj inkrementální seams, strangler slices, ACL, reconciliation a explicitní decommission kritéria. Každý slice musí mít rollback, měření, ownership a přechodový stav. Cílová architektura bez migrační cesty není realizovatelný návrh.
