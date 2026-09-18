
output "project_id" {
  description = "Numeric identifier of the project generic-agent-criteria-source."
  value       = gitlab_project.this.id
}

output "full_path" {
  description = "Fully qualified namespace path of the project."
  value       = gitlab_project.this.path_with_namespace
}
