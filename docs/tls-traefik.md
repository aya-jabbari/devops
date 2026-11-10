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

## Pour Doha (Ingress du chart)

L'Ingress de l'application est dans le périmètre de Doha. Il suffit de réutiliser le Secret `supportops-tls`
(`tls.secretName`) et les deux annotations ci-dessus. Sur la VM cloud, avec un vrai nom de domaine, remplacer ce
certificat par cert-manager + Let's Encrypt : seul le Secret change.

## Nettoyage

```bash
kubectl delete -f deploy/tls/demo-ingress.yaml
```
