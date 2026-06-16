{{/*
Expand the name of the chart.
*/}}
{{- define "bolt-prediction.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a fully qualified app name.
*/}}
{{- define "bolt-prediction.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "bolt-prediction.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "bolt-prediction.labels" -}}
helm.sh/chart: {{ include "bolt-prediction.chart" . }}
{{ include "bolt-prediction.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/part-of: {{ .Values.commonLabels."app.kubernetes.io/part-of" }}
app.kubernetes.io/managed-by: {{ .Values.commonLabels."app.kubernetes.io/managed-by" }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "bolt-prediction.selectorLabels" -}}
app.kubernetes.io/name: {{ include "bolt-prediction.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Component selector labels
*/}}
{{- define "bolt-prediction.componentSelectorLabels" -}}
{{ include "bolt-prediction.selectorLabels" . }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "bolt-prediction.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "bolt-prediction.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Probe helper
*/}}
{{- define "bolt-prediction.probes" -}}
{{- $component := .component -}}
{{- $config := index .Values $component -}}
{{- if $config.probes -}}
{{- if $config.probes.liveness.enabled }}
livenessProbe:
  httpGet:
    path: {{ $config.probes.liveness.path }}
    port: {{ $config.probes.liveness.port }}
  initialDelaySeconds: {{ $config.probes.liveness.initialDelaySeconds }}
  periodSeconds: {{ $config.probes.liveness.periodSeconds }}
  timeoutSeconds: {{ $config.probes.liveness.timeoutSeconds }}
  failureThreshold: {{ $config.probes.liveness.failureThreshold }}
  successThreshold: {{ $config.probes.liveness.successThreshold }}
{{- end }}
{{- if $config.probes.readiness.enabled }}
readinessProbe:
  httpGet:
    path: {{ $config.probes.readiness.path }}
    port: {{ $config.probes.readiness.port }}
  initialDelaySeconds: {{ $config.probes.readiness.initialDelaySeconds }}
  periodSeconds: {{ $config.probes.readiness.periodSeconds }}
  timeoutSeconds: {{ $config.probes.readiness.timeoutSeconds }}
  failureThreshold: {{ $config.probes.readiness.failureThreshold }}
  successThreshold: {{ $config.probes.readiness.successThreshold }}
{{- end }}
{{- if $config.probes.startup.enabled }}
startupProbe:
  httpGet:
    path: {{ $config.probes.startup.path }}
    port: {{ $config.probes.startup.port }}
  initialDelaySeconds: {{ $config.probes.startup.initialDelaySeconds }}
  periodSeconds: {{ $config.probes.startup.periodSeconds }}
  timeoutSeconds: {{ $config.probes.startup.timeoutSeconds }}
  failureThreshold: {{ $config.probes.startup.failureThreshold }}
{{- end }}
{{- end -}}
{{- end -}}

{{/*
Volume mounts helper
*/}}
{{- define "bolt-prediction.volumeMounts" -}}
{{- if .Values.persistence.modelVolume.enabled }}
- name: {{ .Values.persistence.modelVolume.name }}
  mountPath: {{ .Values.persistence.modelVolume.mountPath }}
{{- end }}
{{- if .Values.persistence.dataVolume.enabled }}
- name: {{ .Values.persistence.dataVolume.name }}
  mountPath: {{ .Values.persistence.dataVolume.mountPath }}
{{- end }}
{{- if .Values.persistence.logsVolume.enabled }}
- name: {{ .Values.persistence.logsVolume.name }}
  mountPath: {{ .Values.persistence.logsVolume.mountPath }}
{{- end }}
- name: config-volume
  mountPath: /app/config
  readOnly: true
{{- end -}}

{{/*
Volumes helper
*/}}
{{- define "bolt-prediction.volumes" -}}
{{- if .Values.persistence.modelVolume.enabled }}
- name: {{ .Values.persistence.modelVolume.name }}
  persistentVolumeClaim:
    claimName: {{ include "bolt-prediction.fullname" . }}-models
{{- end }}
{{- if .Values.persistence.dataVolume.enabled }}
- name: {{ .Values.persistence.dataVolume.name }}
  persistentVolumeClaim:
    claimName: {{ include "bolt-prediction.fullname" . }}-data
{{- end }}
{{- if .Values.persistence.logsVolume.enabled }}
- name: {{ .Values.persistence.logsVolume.name }}
  {{- if eq .Values.persistence.logsVolume.accessModes "ReadWriteOnce" }}
  emptyDir: {}
  {{- else }}
  persistentVolumeClaim:
    claimName: {{ include "bolt-prediction.fullname" . }}-logs
  {{- end }}
{{- end }}
- name: config-volume
  configMap:
    name: {{ include "bolt-prediction.fullname" . }}-config
{{- end -}}

{{/*
Environment variables helper
*/}}
{{- define "bolt-prediction.env" -}}
{{- $component := .component -}}
{{- $config := index .Values $component -}}
{{- range $env := $config.env }}
- name: {{ $env.name }}
  {{- if $env.value }}
  value: {{ $env.value | quote }}
  {{- else if $env.valueFrom }}
  valueFrom: {{- toYaml $env.valueFrom | nindent 4 }}
  {{- end }}
{{- end }}
- name: DATABASE_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "bolt-prediction.fullname" . }}-secret
      key: database-password
- name: REDIS_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "bolt-prediction.fullname" . }}-secret
      key: redis-password
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "bolt-prediction.fullname" . }}-secret
      key: jwt-secret-key
- name: API_ENCRYPTION_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "bolt-prediction.fullname" . }}-secret
      key: api-encryption-key
- name: INSTANCE_ID
  valueFrom:
    fieldRef:
      fieldPath: metadata.name
- name: POD_NAME
  valueFrom:
    fieldRef:
      fieldPath: metadata.name
- name: POD_NAMESPACE
  valueFrom:
    fieldRef:
      fieldPath: metadata.namespace
- name: POD_IP
  valueFrom:
    fieldRef:
      fieldPath: status.podIP
{{- end -}}
