{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "kuberag.fullname" -}}
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
{{- define "kuberag.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "kuberag.labels" -}}
helm.sh/chart: {{ include "kuberag.chart" . }}
{{ include "kuberag.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "kuberag.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kuberag.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "kuberag.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "kuberag.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the agent resources
*/}}
{{- define "kuberag.agent" -}}
{{- range .Values.frameworks }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kuberag-agent-{{ .name }}
  namespace: {{ $.Release.Name }}
spec:
  replicas: {{ .replicaCount }}
  selector:
    matchLabels:
      app: kuberag-agent-{{ .name }}
  template:
    metadata:
      labels:
        app: kuberag-agent-{{ .name }}
    spec:
      volumes:
        - name: secret-volume
          secret:
            secretName: {{ $.Release.Name }}-secret
            defaultMode: 384
      containers:
      - name: kuberag
        image: {{ $.Values.AGENT_IMAGE }}
        env:
        - name: LLM_FRAMEWORK
          value: {{ .name }}
        volumeMounts:
          - name: secret-volume
            mountPath: "/etc/secret-volume"
        envFrom:
        - configMapRef:
            name: {{ $.Release.Name }}-cm
        - secretRef:
            name: {{ $.Release.Name }}-secret
        ports:
        - containerPort: 5000
{{- end }}
{{- end -}}

{{- define "kuberag.service" -}}
{{- range .Values.frameworks }}
---
apiVersion: v1
kind: Service
metadata:
  name: kuberag-agent-{{ .name }}
  namespace: {{ $.Release.Name }}
spec:
  selector:
    app: kuberag-agent-{{ .name }}
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
{{- end }}
{{- end -}}
