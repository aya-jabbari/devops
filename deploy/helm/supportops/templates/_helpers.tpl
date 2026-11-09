{{- define "supportops.image" -}}
{{ .Values.backendImage.repository }}:{{ .Values.backendImage.tag }}
{{- end }}

{{- define "supportops.labels" -}}
app.kubernetes.io/name: supportops
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* Env shared by worker and scheduler. */}}
{{- define "supportops.backendEnv" -}}
- name: REDIS_URL
  value: redis://redis:6379/0
- name: SMTP_HOST
  value: {{ .Values.config.smtpHost | quote }}
- name: SMTP_PORT
  value: {{ .Values.config.smtpPort | quote }}
- name: OVERDUE_CHECK_SECONDS
  value: {{ .Values.config.overdueCheckSeconds | quote }}
- name: NOTIFICATION_MAX_RETRIES
  value: {{ .Values.config.notificationMaxRetries | quote }}
{{- range $key := list "DATABASE_URL" "SECRET_KEY" "ALERTMANAGER_WEBHOOK_SECRET" }}
- name: {{ $key }}
  valueFrom:
    secretKeyRef:
      name: {{ $.Values.secrets.existingSecret }}
      key: {{ $key }}
{{- end }}
{{- end }}
