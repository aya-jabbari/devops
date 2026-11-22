# Traefik et TLS

K3s embarque Traefik comme Ingress controller (entrypoints `web` 80 et `websecure` 443). Cette page décrit le
certificat **auto-signé** utilisé en l'absence de nom de domaine (cahier des charges §3.1, Traefik et TLS).

## Mise en place

```bash
scripts/tls-selfsigned.sh                  # crée le Secret TLS supportops-tls (CN supportops.local)
kubectl apply -f deploy/tls/demo-ingress.yaml
```

Le script génère la clé dans un dossier temporaire supprimé à la sortie : **la clé privée n'est jamais écrite dans le dépôt**.
Le Secret est de type `kubernetes.io/tls`, créé à la volée (`--dry-run` puis `apply`), donc rejouable.

L'Ingress de démonstration demande `websecure` et référence `supportops-tls` :

```yaml
annotations:
  traefik.ingress.kubernetes.io/router.entrypoints: websecure
  traefik.ingress.kubernetes.io/router.tls: "true"
spec:
  tls:
    - hosts: [supportops.local]
      secretName: supportops-tls
```

## Vérification (9 novembre 2026, k3d)

```bash
kubectl -n kube-system port-forward svc/traefik 8443:443 &
curl -k --resolve supportops.local:8443:127.0.0.1 https://supportops.local:8443/
```

- Certificat servi : `CN = supportops.local` (auto-signé, émetteur identique).
- Réponse du service de démonstration en HTTPS : OK.
- Sans `-k`, la requête échoue : le certificat n'est pas approuvé, comportement attendu pour un certificat auto-signé.

## HTTPS sur le cluster AWS : certificat par défaut de Traefik

Sur la VM, il n'y a pas de nom de domaine et l'IP publique change à chaque `terraform apply`. Le certificat est donc
généré **après** l'`apply`, pour l'IP du moment :

```bash
scripts/tls-setup.sh            # lit l'IP dans `terraform output public_ip` (ou : scripts/tls-setup.sh <ip>)
```

Le script :

1. crée le Secret `supportops-tls` (auto-signé, 1 an) avec trois noms : `supportops.local`, `<ip-avec-tirets>.sslip.io`
   et l'IP elle-même. `sslip.io` est un DNS public qui résout `56-228-0-126.sslip.io` vers `56.228.0.126` : cela donne
   un vrai nom d'hôte sans acheter de domaine ;
2. applique `deploy/tls/tlsstore.yaml` : un `TLSStore` nommé `default` qui fait de ce certificat le **certificat par
   défaut de Traefik**.

Conséquence : toute route HTTPS sans certificat propre est servie avec `supportops-tls` au lieu du certificat
interne « TRAEFIK DEFAULT CERT ». Sur K3s, l'entrypoint `websecure` (443) a TLS activé par défaut, donc l'Ingress de
l'application répond aussi en HTTPS **sans aucune modification du chart**. HTTP (80) reste ouvert : pas de redirection
forcée tant que le certificat est auto-signé (sinon chaque visiteur tomberait sur l'avertissement du navigateur).

Vérification attendue :

```bash
curl -kv https://<ip-avec-tirets>.sslip.io/health 2>&1 | grep -E 'subject:|subjectAltName|HTTP/'
```

**Vérifié le 22 novembre 2026, sans cluster** : le certificat généré contient bien les trois noms
(`DNS:supportops.local, DNS:56-228-0-126.sslip.io, IP Address:56.228.0.126`), la clé est supprimée du dossier
temporaire, une IP invalide est refusée, et `56-228-0-126.sslip.io` résout vers `56.228.0.126`.
**Reste à vérifier sur le cluster AWS** : `curl` ci-dessus et l'application dans le navigateur.

## Pour Doha (Ingress du chart)

L'Ingress de l'application est dans le périmètre de Doha. Grâce au certificat par défaut ci-dessus, **aucun
changement n'est nécessaire** pour avoir HTTPS. Si elle veut un Ingress explicitement en HTTPS (section `tls`, ou
redirection HTTP vers HTTPS), elle peut réutiliser le Secret `supportops-tls` (`tls.secretName`) et les deux
annotations ci-dessus. Sur la VM cloud, avec un vrai nom de domaine, remplacer ce
certificat par cert-manager + Let's Encrypt : seul le Secret change.

## Nettoyage

```bash
kubectl delete -f deploy/tls/demo-ingress.yaml
```
