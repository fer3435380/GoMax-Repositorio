/// <reference types="cypress" />

describe("Database_create_download_modules", () =>{

    const config = {
        dbName: "GoMax-18", // Name of the database to create
        adminLogin: "admin", // Odoo admin username (for creation and login)
        adminPassword: "admin", // Odoo admin password (for creation and login)
        masterPassword: "natacion", // Master password required to create databases in Odoo
        lang: "es_EC", // Language code (Spanish - Ecuador)
        country: "ec" //Country code (Ecuador)
    };
    it('create_db', () =>{
        cy.visit("http://localhost:8070/web/login")

        cy.url().then((url) =>{
            if (url.includes('/database/selector'))
            {
                cy.get('form[action="/web/database/create"]').first().within(() => {
                cy.get('input[name="master_pwd"]').type(`${config.masterPassword}`)
                cy.get("#dbname").type(`${config.dbName}`)
                cy.get("#login").type(`${config.adminLogin}`)
                cy.get("#password").type(`${config.adminPassword}`)
                cy.get("#lang").select(`${config.lang}`)
                cy.get("#country").select(`${config.country}`)
                cy.contains("Create database").click()
    
                })
            }
            else
            {
                cy.url().should('contain','/login')
            }
        })

        
    })

    it('login_db', () => {

        cy.visit("http://localhost:8070/web/login")
        cy.get("#login").type(`${config.adminLogin}`)
        cy.get("#password").type(`${config.adminPassword}`)
        cy.contains("Iniciar sesión").click()

        cy.task('updateModuleList')

        cy.readFile('../module_list.txt').then((modules) => {
            const lines = modules.split('\n');

            cy.wrap(lines).each((module) => {
                
                cy.visit("http://localhost:8070/odoo/apps")
                cy.get('.o_searchview_input', { timeout: 10000 }).should('be.visible');

                cy.get('.o_facet_remove.oi.oi-close.btn.btn-link.py-0.px-2.text-danger.d-print-none', { timeout: 60000 }).click({timeout: 60000});

                cy.get('.o_searchview_input.o_input.d-print-none.flex-grow-1.w-auto.border-0')
                .clear()
                .type(module + '{enter}')
                cy.wait(500)

                cy.get('body').then($body => {
                    const $btn = $body.find(`button:contains("Activar")`);

                    if($btn.length > 0 && $btn.is(':visible')) {
                        cy.intercept('POST','/web/dataset/call_button/ir.module.module/button_immediate_install').as('installModule');
                        cy.wrap($btn).click({timeout: 60000});

                        cy.wait('@installModule').its('response.statusCode').should('eq', 200);

                    }
                    else
                    {
                        cy.log(`Module ${module} is already installed.`);
                    }
                });
            });
        });
    });
});