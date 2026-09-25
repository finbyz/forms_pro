import { createResource } from "frappe-ui";

export const createNewFormWithDoctype = async (
  linked_doctype: string,
  team_id: string,
  form_name?: string
) => {
  const form = createResource({
    url: "forms_pro.utils.form_generator.create_form_with_doctype",
    makeParams() {
      return {
        doctype: linked_doctype,
        team_id: team_id,
        form_name: form_name,
      };
    },
  });

  await form.fetch();
  return form.data;
};

export const createNewForm = async (team_id: string, form_name: string) => {
  const form = createResource({
    url: "forms_pro.utils.form_generator.create_form",
    makeParams() {
      return {
        team_id: team_id,
        form_name: form_name,
      };
    },
  });

  await form.fetch();
  return form.data;
};

/** The form name doubles as the DocType name, so it must be unique. */
export const checkFormNameAvailable = async (
  form_name: string
): Promise<{ name: string; available: boolean }> => {
  const check = createResource({
    url: "forms_pro.utils.form_generator.check_form_name_available",
    makeParams() {
      return { form_name };
    },
  });
  await check.fetch();
  return check.data;
};

export const validateFormRoute = async (
  curr_form_id: string,
  route: string
) => {
  const route_exists = createResource({
    url: "frappe.client.get_count",
    makeParams() {
      return {
        doctype: "Form",
        filters: {
          name: ["!=", curr_form_id],
          route: route,
        },
      };
    },
  });

  await route_exists.fetch();
  return route_exists.data > 0;
};
