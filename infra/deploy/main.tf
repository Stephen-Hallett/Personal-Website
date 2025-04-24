data "azurerm_client_config" "current" {}

data "azurerm_subscription" "primary" {}

data "azurerm_resource_group" "rg" {
  name = "rg-${var.project_id}-${var.env}-ea-001"
}

resource "azurerm_static_web_app" "app" {
  name                = "app-${var.project_id}-${var.env}-ea-001"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
}

