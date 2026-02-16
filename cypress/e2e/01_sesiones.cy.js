describe('Giftcards - Temporadas (crear y editar)', () => {

  beforeEach(() => {
    Cypress.on('uncaught:exception', (err) => {
      if (err.message.includes('parentNode')) {
        return false
      }
      return true
    })

    cy.session('admin-session', () => {
      cy.visit('http://localhost:8070/web/login')

      cy.get('input[name="login"]').type('admin')
      cy.get('input[name="password"]').type('admin')
      cy.get('button[type="submit"]').click()
      cy.url().should('include', '/odoo')
    })

    cy.visit('http://localhost:8070/odoo')
    cy.contains('Giftcards').click()
    cy.contains('Temporadas').click()
  })

  it('Crea una temporada', () => {
    cy.contains('Nuevo').click()

    const seasonName = 'Temporada Cypress'
    Cypress.env('seasonName', seasonName)

    cy.wait(1000) // Esperar a que cargue las opciones dependientes

    cy.get('div[name="name"] input').clear({ force: true }).type(seasonName)

    cy.wait(1000) // Esperar a que cargue las opciones dependientes

    cy.get('div[name="start_date"] input')
      .clear({ force: true })
      .type('2025-12-10', { force: true })

    cy.wait(1000) // Esperar a que cargue las opciones dependientes

    cy.get('div[name="end_date"] input')
      .clear({ force: true })
      .type('2025-12-31', { force: true })
      
    cy.wait(1000) // Esperar a que cargue las opciones dependientes

    cy.get('button.o_form_button_save').click()

    // Volver al listado
    cy.visit('http://localhost:8070/odoo')

    cy.wait(500) // Esperar a que cargue las opciones dependientes

    cy.contains('Giftcards').click()

    cy.wait(500) // Esperar a que cargue las opciones dependientes

    cy.contains('Temporadas').click()

    cy.wait(500) // Esperar a que cargue las opciones dependientes

    cy.contains(seasonName).should('exist')
  })

  it('Edita la temporada creada', () => {
    const seasonName = Cypress.env('seasonName')
    const editedName = 'Temporada Editada Cypress'

    expect(seasonName).to.exist

    cy.contains(seasonName).click()

    const startPlusOne = new Date('2025-12-10')
    startPlusOne.setDate(startPlusOne.getDate() + 1)
    const newStartDate = startPlusOne.toISOString().split('T')[0]

    cy.wait(1000) // Esperar a que cargue las opciones dependientes

    cy.get('div[name="name"] input')
      .clear({ force: true })
      .type(editedName, { force: true })

    cy.wait(1000) // Esperar a que cargue las opciones dependientes

    cy.get('div[name="start_date"] input')
      .clear({ force: true })
      .type(newStartDate, { force: true })

    cy.wait(1000) // Esperar a que cargue las opciones dependientes

    cy.get('div[name="end_date"] input')
      .clear({ force: true })
      .type('2026-01-31', { force: true })

    cy.wait(1000) // Esperar a que cargue las opciones dependientes

    cy.get('button.o_form_button_save').click()

    cy.wait(500) // Esperar a que cargue las opciones dependientes

    cy.contains('Giftcards').click()

    cy.wait(500) // Esperar a que cargue las opciones dependientes

    cy.contains('Temporadas').click()

    cy.wait(500) // Esperar a que cargue las opciones dependientes

    cy.contains(editedName).should('exist')
  })

})
