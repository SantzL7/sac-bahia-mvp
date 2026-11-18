terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}
variable "aws_region" {type=string,default="sa-east-1"}
provider "aws" {region=var.aws_region}
resource "aws_secretsmanager_secret" "sac_credentials" {
  name_prefix = "sac-bahia-tde-"
  description = "Segredo de demonstração do TDE SAC Bahia; remover após a avaliação."
  recovery_window_in_days = 7
}
resource "aws_iam_policy" "sac_secret_reader" {
  name_prefix = "sac-bahia-tde-read-"
  description = "Permite leitura apenas do segredo acadêmico SAC Bahia. Atribuir a uma identidade autorizada."
  policy = jsonencode({
    Version="2012-10-17"
    Statement=[{Effect="Allow",Action=["secretsmanager:GetSecretValue"],Resource=aws_secretsmanager_secret.sac_credentials.arn}]
  })
}
output "secret_arn" {value=aws_secretsmanager_secret.sac_credentials.arn}
output "reader_policy_arn" {value=aws_iam_policy.sac_secret_reader.arn}
