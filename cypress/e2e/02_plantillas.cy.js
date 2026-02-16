describe('Giftcards - Plantillas (crear y editar)', () => {

  beforeEach(() => {
    // Ignorar error interno de Odoo
    Cypress.on('uncaught:exception', (err) => {
      if (err.message.includes('parentNode')) {
        return false
      }
      return true
    })

    // Sesión persistente (NO vuelve a logear)
    cy.session('admin-session', () => {
      cy.visit('http://localhost:8070/web/login')

      cy.get('input[name="login"]').type('admin')
      cy.get('input[name="password"]').type('admin')
      cy.get('button[type="submit"]').click()
      cy.url().should('include', '/odoo')
    })

    // Entrar siempre desde estado limpio
    cy.visit('http://localhost:8070/odoo')
    cy.contains('Giftcards').click()
    cy.contains('Plantillas').click()
  })

  it('Crea una plantilla de giftcard', () => {
    cy.contains('Nuevo').click()

    const templateName = 'Plantilla Cypress'
    Cypress.env('templateName', templateName)

    // Nombre
    cy.get('div[name="name"] input').type(templateName)

    cy.wait(500)

    // Descripción
    cy.get('div[name="description"] textarea')
      .type('Plantilla creada automáticamente por Cypress')

    cy.wait(500)

    // Límite de giftcards
    cy.get('div[name="giftcard_limit"] input')
      .clear({ force: true })
      .type('20', { force: true })

    cy.wait(500)
    
    // Franquicias (many2many_tags)
    cy.get('div[name="franchise_ids"] input')
      .type('Franquicia A', { force: true })
      .type('{enter}')

    cy.wait(500)

    // Producto (many2one)
    cy.get('div[name="product_id"] input')
      .type('Plan A', { force: true })
      .type('{enter}')

    cy.wait(1000)

    // Temporada (many2one)
    cy.get('div[name="season_id"] input')
      .type('Temporada Editada Cypress', { force: true })
      .type('{enter}')

    cy.wait(1000)

    // Permanencia (many2one)
    cy.get('div[name="permanence_id"] input')
      .type('Fecha fija', { force: true })
      .type('{enter}')

    cy.wait(500)

    // Fecha inicio
    cy.get('div[name="start_date"] input')
      .clear({ force: true })
      .type('2025-12-10', { force: true })

    cy.wait(500)

    // Fecha fin
    cy.get('div[name="end_date"] input')
      .clear({ force: true })
      .type('2025-12-31', { force: true })

    cy.wait(500)

    // Guardar
    cy.get('button.o_form_button_save').click()

    // Volver al listado
    cy.visit('http://localhost:8070/odoo')
    cy.contains('Giftcards').click()
    cy.contains('Plantillas').click()

    cy.contains(templateName).should('exist')
  })

  it('Edita la plantilla creada', () => {
    const templateName = Cypress.env('templateName')
    const editedName = 'Plantilla Editada Cypress'

    cy.contains(templateName).click()

    // Editar nombre
    cy.get('div[name="name"] input')
      .clear({ force: true })
      .type(editedName, { force: true })
  
    cy.wait(500)

    // Editar descripción
    cy.get('div[name="description"] textarea')
      .clear({ force: true })
      .type('Plantilla editada automáticamente por Cypress')

    cy.wait(500)

    // Editar límite
    cy.get('div[name="giftcard_limit"] input')
      .clear({ force: true })
      .type('40', { force: true })

    cy.wait(500)

    // Nueva fecha fin
    cy.get('div[name="end_date"] input')
      .clear({ force: true })
      .type('2026-01-31', { force: true })

    cy.wait(500)
    
    // Guardar cambios
    cy.get('button.o_form_button_save').click()

    // Volver al listado
    cy.contains('Giftcards').click()
    cy.contains('Plantillas').click()

    cy.contains(editedName).should('exist')
  })

})
