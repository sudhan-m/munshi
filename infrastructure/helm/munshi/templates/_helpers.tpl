{{/*
Expand the name of the chart.
*/}}
{{- define "munshi.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "munshi.fullname" -}}
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
{{- define "munshi.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "munshi.labels" -}}
helm.sh/chart: {{ include "munshi.chart" . }}
{{ include "munshi.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
environment: {{ .Values.environment }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "munshi.selectorLabels" -}}
app.kubernetes.io/name: {{ include "munshi.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
API Gateway labels
*/}}
{{- define "munshi.apiGatewayLabels" -}}
{{ include "munshi.labels" . }}
app.kubernetes.io/component: api-gateway
{{- end }}

{{/*
Auth Service labels
*/}}
{{- define "munshi.authServiceLabels" -}}
{{ include "munshi.labels" . }}
app.kubernetes.io/component: auth-service
{{- end }}

{{/*
Image name helper
*/}}
{{- define "munshi.apiGatewayImage" -}}
{{- if .Values.global.imageRegistry }}
{{- printf "%s/%s:%s" .Values.global.imageRegistry .Values.images.apiGateway.repository .Values.images.apiGateway.tag }}
{{- else }}
{{- printf "%s:%s" .Values.images.apiGateway.repository .Values.images.apiGateway.tag }}
{{- end }}
{{- end }}

{{- define "munshi.authServiceImage" -}}
{{- if .Values.global.imageRegistry }}
{{- printf "%s/%s:%s" .Values.global.imageRegistry .Values.images.authService.repository .Values.images.authService.tag }}
{{- else }}
{{- printf "%s:%s" .Values.images.authService.repository .Values.images.authService.tag }}
{{- end }}
{{- end }}

{{/*
ServiceAccount name
*/}}
{{- define "munshi.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "munshi.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Linkerd service mesh annotations
*/}}
{{- define "munshi.linkerdAnnotations" -}}
{{- if .Values.linkerd.enabled }}
linkerd.io/inject: {{ .Values.linkerd.inject.default }}
config.linkerd.io/proxy-cpu-request: {{ .Values.linkerd.controlPlane.proxy.resources.cpu.request }}
config.linkerd.io/proxy-memory-request: {{ .Values.linkerd.controlPlane.proxy.resources.memory.request }}
config.linkerd.io/proxy-cpu-limit: {{ .Values.linkerd.controlPlane.proxy.resources.cpu.limit }}
config.linkerd.io/proxy-memory-limit: {{ .Values.linkerd.controlPlane.proxy.resources.memory.limit }}
{{- end }}
{{- end }}