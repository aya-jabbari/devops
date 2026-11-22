# Rapport de coûts : infrastructure cloud

Livrable du pôle Aya (cahier des charges v2.1, §5 et §7). Version de travail : complétée après chaque session cloud,
finalisée en semaine 5.

## Contexte

| Élément | Valeur |
|---|---|
| Fournisseur | AWS, compte de l'équipe sur le **Free plan** |
| Crédits | 120 $ à l'ouverture, expiration le 8 mai 2027 |
| Région | `eu-north-1` (Stockholm) : le Free plan verrouille le compte sur cette région |
| Instance | `m7i-flex.large` (2 vCPU, 8 Go), seul type éligible Free plan assez grand pour la pile complète |
| Disque | gp3 30 Go, chiffré, supprimé avec l'instance |
| Réseau | 1 IP élastique (IPv4 publique facturée à l'heure), VPC, sous-réseau, passerelle : gratuits |
| Règle | `terraform destroy` à la fin de chaque session : rien ne tourne entre deux sessions |

## Journal des sessions

Heures en UTC. Durée facturée de l'instance : de sa création à sa destruction.

| # | Date | Création | Destruction | Durée instance | Activité | Crédits après |
|---|---|---|---|---|---|---|
| 1 | 22/11/2026 | 12:32 (réseau, IP) · 12:36 (instance) | 13:24 | ~48 min | Premier `apply`, K3s, secrets SOPS, déploiement Helm, persistance PVC, acte 5 | 139,99 $ (*) |

(*) Le solde de crédits a augmenté de 20 $ après la session (crédit d'activité du Free plan probablement accordé pour le
premier lancement EC2). La facturation AWS est publiée avec un délai : le coût réel de la session est à relever le
lendemain dans **Billing and Cost Management > Cost Explorer**, filtré sur `eu-north-1`.

## Vérification après destruction (session 1)

`terraform state list` vide ; dans `eu-north-1` : 0 instance, 0 IP élastique, 0 volume EBS, 0 paire de clés ; seul reste
le VPC par défaut du compte (gratuit, préexistant).

## À compléter

- Prix unitaires relevés dans la console : instance `m7i-flex.large` à l'heure, IPv4 publique à l'heure, gp3 au Go-mois.
- Coût réel par session (Cost Explorer) et total consommé sur les crédits.
- Projection : coût d'une semaine allumée en continu, comparé au fonctionnement « une session, puis destroy ».
