# Rapport de coûts : infrastructure cloud

Livrable du pôle Aya (cahier des charges v2.1, §5 et §7). Version de travail : complétée après chaque session cloud,
finalisée en semaine 5.

## Contexte

| Élément | Valeur |
|---|---|
| Fournisseur | AWS, compte de l'équipe sur le **Free plan** |
| Crédits | 120 $ à l'ouverture, 139,99 $ après la session 1 (voir plus bas), expiration le 8 mai 2027 |
| Région | `eu-north-1` (Stockholm) : le Free plan verrouille le compte sur cette région |
| Instance | `m7i-flex.large` (2 vCPU, 8 Go), seul type éligible Free plan assez grand pour la pile complète |
| Disque | gp3 30 Go, chiffré, supprimé avec l'instance |
| Réseau | 1 IP élastique (IPv4 publique facturée à l'heure) ; VPC, sous-réseau, passerelle, groupe de sécurité : gratuits |
| Règle | `terraform destroy` à la fin de chaque session : rien ne tourne entre deux sessions |

## Prix unitaires (`eu-north-1`, à la demande, Linux)

Relevés le 22 novembre 2026 dans les fichiers de prix publics d'AWS (Price List, publication du 21 novembre 2026).
Les montants sont en dollars US hors taxes.

| Ressource | Prix unitaire | Ramené à l'heure | Source |
|---|---|---|---|
| Instance `m7i-flex.large` | 0,10175 $ / h | **0,1018 $** | Price List EC2, Linux, Stockholm |
| Disque gp3 30 Go | 0,0836 $ / Go-mois | **0,0034 $** (30 × 0,0836 / 730 h) | Price List EC2, `EUN1-EBS:VolumeUsage.gp3` |
| IPv4 publique (IP élastique) | 0,005 $ / h, attachée ou non | **0,0050 $** | Price List VPC, `EUN1-PublicIPv4:InUseAddress` |
| VPC, sous-réseau, passerelle Internet, groupe de sécurité | gratuit | 0 | n/a |
| Trafic sortant | 100 Go/mois offerts par AWS, négligeable pour une démo | ≈ 0 | n/a |
| **Total infrastructure allumée** | | **≈ 0,110 $ / h** | |

L'instance représente 92 % du coût horaire. Pour comparaison, au même endroit :

| Type | vCPU / RAM | Prix / h | Mois 24/7 (avec disque et IP) | Utilisable ? |
|---|---|---|---|---|
| `t3.medium` | 2 / 4 Go | 0,0432 $ | 37,69 $ | Non : refusé par le Free plan |
| `c7i-flex.large` | 2 / 4 Go | 0,0908 $ | 72,42 $ | Oui, mais 4 Go est juste pour K3s + Argo CD + Prometheus |
| **`m7i-flex.large`** | 2 / 8 Go | 0,1018 $ | **80,44 $** | **Oui (choisi)** : seulement 12 % plus cher que `c7i-flex.large` pour deux fois plus de mémoire |

## Journal des sessions

Heures en UTC. L'instance est facturée à la seconde (minimum 60 s), du lancement à la destruction ; l'IP élastique,
de son allocation à sa libération.

| # | Date | Allocation IP | Instance créée | Destruction | Durée instance | Durée IP | Activité |
|---|---|---|---|---|---|---|---|
| 1 | 22/11/2026 | 12:33 | 12:36 | 13:23-13:24 | 47 min (0,78 h) | 52 min (0,86 h) | Premier `apply`, K3s, secrets SOPS, déploiement Helm, persistance PVC, acte 5, `destroy` |

### Coût de la session 1

| Poste | Calcul | Estimation | Réel (Cost Explorer) |
|---|---|---|---|
| Instance | 0,784 h × 0,10175 $ | 0,080 $ | à relever |
| Disque gp3 | 0,784 h × 0,00344 $ | 0,003 $ | à relever |
| IPv4 publique | 0,863 h × 0,005 $ | 0,004 $ | à relever |
| **Total** | | **≈ 0,09 $** | à relever |

Montant payé : **0 $**, l'usage est couvert par les crédits du Free plan.

Le solde de crédits est passé de 120 $ à 139,99 $ après la session : AWS accorde des crédits supplémentaires pour certaines
activités de découverte, dont le premier lancement d'une instance EC2. La facturation est publiée avec un délai
(jusqu'à 24 h) : le 22 novembre à 13:30 UTC, Cost Explorer affichait encore 0 $ pour la journée.

Relever le coût réel (le lendemain) :

```bash
AWS_PROFILE=supportops aws ce get-cost-and-usage --region us-east-1 \
  --time-period Start=2026-11-22,End=2026-11-23 --granularity DAILY \
  --metrics UnblendedCost UsageQuantity --group-by Type=DIMENSION,Key=USAGE_TYPE
```

### Vérification après destruction (session 1)

`terraform state list` vide ; dans `eu-north-1` : 0 instance, 0 IP élastique, 0 volume EBS, 0 paire de clés. Seul reste
le VPC par défaut du compte (gratuit, préexistant).

## Projections

Sur la base de 0,110 $ / h pour l'infrastructure allumée.

| Scénario | Durée | Coût | Part des 139,99 $ de crédits |
|---|---|---|---|
| Une session de travail | 3 h | 0,33 $ | 0,2 % |
| Jour de la démonstration (répétition + soutenance) | 8 h | 0,88 $ | 0,6 % |
| **Plan prévu jusqu'à la soutenance** : 12 sessions de 3 h + jour de démo | 44 h | **4,85 $** | **3,5 %** |
| Infrastructure oubliée allumée une semaine | 168 h | 18,51 $ | 13 % |
| Infrastructure allumée en continu un mois | 730 h | 80,44 $ | 57 % |
| Instance détruite mais IP élastique oubliée, un mois | 730 h | 3,65 $ | 2,6 % |

Les crédits couvrent environ **1 270 heures** d'infrastructure allumée, soit plus de 50 jours en continu : ils ne sont pas
une contrainte pour le projet, tant que la règle « une session, puis `destroy` » est tenue. Le risque principal est
l'oubli : une semaine allumée coûte autant que 56 sessions de 3 heures.

## Mesures de maîtrise des coûts

- `terraform destroy` à chaque fin de session, puis vérification qu'il ne reste ni instance, ni IP élastique, ni volume.
- Disque supprimé avec l'instance (`delete_on_termination = true`) : aucun volume orphelin.
- Une seule IP publique (IP élastique), pas d'IP publique automatique sur le sous-réseau.
- Un seul nœud, une seule région, aucun service managé payant (base de données, équilibreur de charge, NAT).
- Budget AWS avec alertes e-mail (guide `docs/guide-acces-aws.md`, étape A4) et alertes Free plan.

## À compléter

- Coût réel de chaque session relevé dans Cost Explorer (colonne « Réel »).
- Nouvelles sessions dans le journal, avec leur activité.
- Bilan final (semaine 5) : total consommé, écart entre estimation et réel, crédits restants.
