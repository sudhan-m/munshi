{{/*
Expand the name of the chart.
*/}}
{{- define "munshi-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "munshi-platform.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "munshi-platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "munshi-platform.labels" -}}
helm.sh/chart: {{ include "munshi-platform.chart" . }}
{{ include "munshi-platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "munshi-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "munshi-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service-specific labels
*/}}
{{- define "munshi-platform.serviceLabels" -}}
{{- $serviceName := .serviceName -}}
app.kubernetes.io/name: {{ include "munshi-platform.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ $serviceName }}
helm.sh/chart: {{ include "munshi-platform.chart" .root }}
{{- if .root.Chart.AppVersion }}
app.kubernetes.io/version: {{ .root.Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "munshi-platform.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "munshi-platform.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Get image name for a service
*/}}
{{- define "munshi-platform.image" -}}
{{- $service := .service -}}
{{- $root := .root -}}
{{- $registry := $root.Values.global.imageRegistry | default $root.Values.image.registry -}}
{{- $repository := $service.image.repository -}}
{{- $tag := $service.image.tag | default $root.Values.image.tag | default $root.Chart.AppVersion -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else -}}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}

{{/*
Common environment variables for all services
*/}}
{{- define "munshi-platform.commonEnv" -}}
- name: ENVIRONMENT
  value: {{ .Values.environment | quote }}
- name: LOG_LEVEL
  value: {{ .Values.logging.level | quote }}
- name: LOG_FORMAT
  value: {{ .Values.logging.format | quote }}
{{- end }}

{{/*
Health check configuration
*/}}
{{- define "munshi-platform.livenessProbe" -}}
{{- if .Values.healthChecks.enabled }}
livenessProbe:
  {{- toYaml .Values.healthChecks.livenessProbe | nindent 2 }}
{{- end }}
{{- end }}

{{- define "munshi-platform.readinessProbe" -}}
{{- if .Values.healthChecks.enabled }}
readinessProbe:
  {{- toYaml .Values.healthChecks.readinessProbe | nindent 2 }}
{{- end }}
{{- end }}

{{/*
Security context
*/}}
{{- define "munshi-platform.securityContext" -}}
{{- toYaml .Values.securityContext | nindent 2 }}
{{- end }}

{{/*
Pod security context
*/}}
{{- define "munshi-platform.podSecurityContext" -}}
{{- toYaml .Values.podSecurityContext | nindent 2 }}
{{- end }}

{{/*
Resource limits and requests
*/}}
{{- define "munshi-platform.resources" -}}
{{- $serviceResources := .service.resources | default dict -}}
{{- $globalResources := .root.Values.resources | default dict -}}
{{- $resources := mergeOverwrite $globalResources $serviceResources -}}
{{- if $resources }}
resources:
  {{- toYaml $resources | nindent 2 }}
{{- end }}
{{- end }}

{{/*
Node selector
*/}}
{{- define "munshi-platform.nodeSelector" -}}
{{- $serviceNodeSelector := .service.nodeSelector | default dict -}}
{{- $globalNodeSelector := .root.Values.nodeSelector | default dict -}}
{{- $nodeSelector := mergeOverwrite $globalNodeSelector $serviceNodeSelector -}}
{{- if $nodeSelector }}
nodeSelector:
  {{- toYaml $nodeSelector | nindent 2 }}
{{- end }}
{{- end }}

{{/*
Tolerations
*/}}
{{- define "munshi-platform.tolerations" -}}
{{- $serviceTolerations := .service.tolerations | default list -}}
{{- $globalTolerations := .root.Values.tolerations | default list -}}
{{- $tolerations := concat $globalTolerations $serviceTolerations -}}
{{- if $tolerations }}
tolerations:
  {{- toYaml $tolerations | nindent 2 }}
{{- end }}
{{- end }}

{{/*
Affinity
*/}}
{{- define "munshi-platform.affinity" -}}
{{- $serviceAffinity := .service.affinity | default dict -}}
{{- $globalAffinity := .root.Values.affinity | default dict -}}
{{- $affinity := mergeOverwrite $globalAffinity $serviceAffinity -}}
{{- if $affinity }}
affinity:
  {{- toYaml $affinity | nindent 2 }}
{{- end }}
{{- end }}