describe('Giftcards - Órdenes de Giftcard', () => {

  beforeEach(() => {
    // Ignorar error interno de Odoo
    Cypress.on('uncaught:exception', (err) => {
      if (err.message.includes('parentNode')) {
        return false
      }
      return true
    })

    // Sesión persistente
    cy.session('admin-session', () => {
      cy.visit('http://localhost:8070/web/login')

      cy.get('input[name="login"]').type('admin')
      cy.get('input[name="password"]').type('admin')
      cy.get('button[type="submit"]').click()
      cy.url().should('include', '/odoo')
    })

    // Entrar limpio
    cy.visit('http://localhost:8070/odoo/sales')
    cy.contains('Órdenes').click()
    cy.contains('Órdenes Giftcards').click()

  })

  it('Crea una orden de giftcard', () => {
    cy.contains('Nuevo').click()

    // ---------- Cliente ----------
    cy.get('div[name="partner_id"] input')
      .type('Cliente Prueba', { force: true })

    cy.wait(500)

    cy.get('.ui-autocomplete li')
      .contains('Cliente Prueba')
      .click()

    cy.wait(1000)

    // ---------- Plantilla ----------
    cy.get('div[name="gift_template_id"] input')
      .type('Plantilla Editada Cypress', { force: true })

    cy.wait(500)

    cy.get('.ui-autocomplete li')
      .contains('Plantilla Editada Cypress')
      .click()

    cy.wait(1000)

    // ---------- Franquicia ----------
    cy.get('div[name="franchise_id"] input')
      .type('Franquicia A', { force: true })

    cy.wait(500)

    cy.get('.ui-autocomplete li')
      .contains('Franquicia A')
      .click()

    cy.wait(1000)

    // Guardar
    cy.get('button.o_form_button_save').click()

    cy.wait(1000)

    // Volver al listado
    cy.visit('http://localhost:8070/odoo/sales')

    cy.wait(500)

    cy.contains('Órdenes').click()

    cy.wait(500)
    
    cy.contains('Órdenes Giftcards').click()
  })


})