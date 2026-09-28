import {
  ConditionalLogic,
  ConditionalOperators,
  Condition,
  Actions,
} from "@/types/conditional-render.types";
import { FormField, Fieldtype } from "@/types/formfield";
import { getFieldTypeDef } from "@/config/fieldTypes";

/**
 * Parse conditional_logic string into ConditionalLogic object
 */
export function parseConditionalLogic(
  conditionalLogic: string | undefined | null
): ConditionalLogic | null {
  if (!conditionalLogic || conditionalLogic.trim() === "") {
    return null;
  }

  try {
    return JSON.parse(conditionalLogic) as ConditionalLogic;
  } catch (e) {
    console.error("Failed to parse conditional_logic:", e);
    return null;
  }
}

/**
 * Convert boolean-like values (1, "1", true, "true", "yes", etc.) to boolean
 */
export function toBoolean(val: any): boolean {
  if (val === null || val === undefined || val === "") return false;
  if (typeof val === "boolean") return val;
  if (typeof val === "number") return val === 1;
  if (typeof val === "string") {
    const s = val.trim().toLowerCase();
    return s === "1" || s === "true" || s === "yes" || s === "checked" || s === "on";
  }
  return false;
}

/**
 * Check if a fieldtype represents a boolean switch/check
 */
export function isBooleanFieldType(fieldType?: string): boolean {
  if (!fieldType) return false;
  if (["Check", "Checkbox", "Switch"].includes(fieldType)) return true;
  const typeDef = getFieldTypeDef(fieldType as Fieldtype);
  return Boolean(typeDef?.isBoolean);
}

/**
 * Parse a numeric value, stripping commas and formatting
 */
export function toNumber(val: any): number | null {
  if (val === null || val === undefined || val === "") return null;
  if (typeof val === "number") return isNaN(val) ? null : val;
  const cleaned = String(val).replace(/,/g, "").trim();
  const num = Number(cleaned);
  return isNaN(num) ? null : num;
}


/**
 * Evaluate a single condition against form field values
 */
function evaluateCondition(
  condition: Condition,
  formValues: Record<string, any>,
  allFields: FormField[]
): boolean {
  const { fieldname, operator, value } = condition;
  if (!fieldname) return false;

  // Get the field definition to understand its type
  const field = allFields.find((f) => f.fieldname === fieldname);
  if (!field) {
    console.warn(`Field ${fieldname} not found in form fields`);
    return false;
  }

  const rawFieldValue = formValues[fieldname];
  const fieldType = field.fieldtype;

  // 1. Handle Boolean fields (Checkbox, Switch)
  if (isBooleanFieldType(fieldType)) {
    const actualBool = toBoolean(rawFieldValue);
    const expectedBool = toBoolean(value);

    switch (operator) {
      case ConditionalOperators.Is:
        return actualBool === expectedBool;

      case ConditionalOperators.IsNot:
        return actualBool !== expectedBool;

      case ConditionalOperators.IsEmpty:
        return !actualBool;

      case ConditionalOperators.IsNotEmpty:
      case ConditionalOperators.IsSet:
        return actualBool;

      default:
        return actualBool === expectedBool;
    }
  }

  // 2. Handle Numeric fields (Number, Currency, etc.)
  const isNumericField = ["Number", "Currency", "Float", "Int", "Percent"].includes(fieldType);
  const actualNum = toNumber(rawFieldValue);
  const expectedNum = toNumber(value);

  if (isNumericField && actualNum !== null && expectedNum !== null) {
    switch (operator) {
      case ConditionalOperators.Is:
        return actualNum === expectedNum;

      case ConditionalOperators.IsNot:
        return actualNum !== expectedNum;

      case ConditionalOperators.IsLessThan:
        return actualNum < expectedNum;

      case ConditionalOperators.IsLessThanOrEqualTo:
        return actualNum <= expectedNum;

      case ConditionalOperators.IsGreaterThan:
        return actualNum > expectedNum;

      case ConditionalOperators.IsGreaterThanOrEqualTo:
        return actualNum >= expectedNum;
    }
  }

  // 3. String & Select comparisons (case-insensitive & whitespace trimmed)
  const actualStr =
    rawFieldValue !== null && rawFieldValue !== undefined ? String(rawFieldValue).trim() : null;
  const expectedStr =
    value !== null && value !== undefined ? String(value).trim() : null;

  const actualLower = actualStr ? actualStr.toLowerCase() : "";
  const expectedLower = expectedStr ? expectedStr.toLowerCase() : "";

  switch (operator) {
    case ConditionalOperators.Is:
      return actualLower === expectedLower;

    case ConditionalOperators.IsNot:
      return actualLower !== expectedLower;

    case ConditionalOperators.IsEmpty:
      return (
        rawFieldValue === null ||
        rawFieldValue === undefined ||
        rawFieldValue === "" ||
        (Array.isArray(rawFieldValue) && rawFieldValue.length === 0)
      );

    case ConditionalOperators.IsNotEmpty:
    case ConditionalOperators.IsSet:
      return (
        rawFieldValue !== null &&
        rawFieldValue !== undefined &&
        rawFieldValue !== "" &&
        (!Array.isArray(rawFieldValue) || rawFieldValue.length > 0)
      );

    case ConditionalOperators.Contains:
      if (!actualStr) return false;
      return actualLower.includes(expectedLower);

    case ConditionalOperators.DoesNotContain:
      if (!actualStr) return true;
      return !actualLower.includes(expectedLower);

    case ConditionalOperators.StartsWith:
      if (!actualStr) return false;
      return actualLower.startsWith(expectedLower);

    case ConditionalOperators.DoesNotStartWith:
      if (!actualStr) return true;
      return !actualLower.startsWith(expectedLower);

    case ConditionalOperators.EndsWith:
      if (!actualStr) return false;
      return actualLower.endsWith(expectedLower);

    case ConditionalOperators.DoesNotEndWith:
      if (!actualStr) return true;
      return !actualLower.endsWith(expectedLower);

    case ConditionalOperators.IsLessThan:
      if (actualNum !== null && expectedNum !== null) {
        return actualNum < expectedNum;
      }
      return false;

    case ConditionalOperators.IsLessThanOrEqualTo:
      if (actualNum !== null && expectedNum !== null) {
        return actualNum <= expectedNum;
      }
      return false;

    case ConditionalOperators.IsGreaterThan:
      if (actualNum !== null && expectedNum !== null) {
        return actualNum > expectedNum;
      }
      return false;

    case ConditionalOperators.IsGreaterThanOrEqualTo:
      if (actualNum !== null && expectedNum !== null) {
        return actualNum >= expectedNum;
      }
      return false;

    default:
      console.warn(`Unknown operator: ${operator}`);
      return false;
  }
}

/**
 * Evaluate all conditions in a ConditionalLogic object
 * Currently supports AND logic (all conditions must be true)
 */
function evaluateConditions(
  conditionalLogic: ConditionalLogic,
  formValues: Record<string, any>,
  allFields: FormField[]
): boolean {
  if (
    !conditionalLogic.conditions ||
    conditionalLogic.conditions.length === 0
  ) {
    return false;
  }

  // All conditions must be true (AND logic)
  return conditionalLogic.conditions.every((condition) =>
    evaluateCondition(condition, formValues, allFields)
  );
}

/**
 * Check if a fieldtype represents a step or section separator (Page Break, Section Break)
 */
export function isStepSeparator(fieldType?: string): boolean {
  if (!fieldType) return false;
  return (
    fieldType === "Page Break" ||
    fieldType === "Tab Break" ||
    fieldType === "Section Break" ||
    fieldType === Fieldtype.PAGE_BREAK
  );
}

/**
 * Every fieldname that sits inside a step / section, in form order.
 */
export function getFieldnamesInSection(
  separatorFieldname: string,
  allFields: FormField[]
): string[] {
  let inSection = false;
  const fieldsInSection: string[] = [];

  for (const f of allFields) {
    if (isStepSeparator(f.fieldtype)) {
      if (f.fieldname === separatorFieldname) {
        inSection = true;
        continue;
      } else if (inSection) {
        break;
      }
    } else if (inSection) {
      fieldsInSection.push(f.fieldname);
    }
  }

  return fieldsInSection;
}

/**
 * Get all fieldnames governed by a step / section separator.
 *
 * Targeting a step means the whole step: every field in it follows the rule.
 *
 * A rule whose own trigger sits inside the step it targets is self-referential
 * -- answering the question would hide the question. It used to be honoured
 * partially, governing only the fields *after* the trigger, which is what made
 * a rule on "Existing Company?" quietly hide Company Address and Customer, two
 * fields nobody had pointed it at. Such a rule governs nothing instead; the
 * builder no longer offers that target, so it can only come from an older form.
 */
export function getGovernedFieldnames(
  separatorFieldname: string,
  allFields: FormField[],
  triggerFieldnames: string[] = []
): string[] {
  const fieldsInSection = getFieldnamesInSection(separatorFieldname, allFields);

  if (triggerFieldnames.some((name) => fieldsInSection.includes(name))) {
    return [];
  }

  return fieldsInSection;
}

/**
 * Find all conditional logic rules that target a given field, either directly
 * or via an enclosing Step / Section Break.
 */
function findTargetingRules(field: FormField, allFields: FormField[]): ConditionalLogic[] {
  const targetingRules: ConditionalLogic[] = [];

  allFields.forEach((otherField) => {
    if (!otherField.conditional_logic) return;

    const logic = parseConditionalLogic(otherField.conditional_logic);
    if (!logic) return;

    const rawTarget = logic.target_field || otherField.fieldname;
    const targets = Array.isArray(rawTarget) ? rawTarget : [rawTarget];
    const triggerFields = (logic.conditions || []).map((c) => c.fieldname).filter(Boolean);

    let isTargeted = targets.includes(field.fieldname);
    if (!isTargeted) {
      for (const tgt of targets) {
        const governed = getGovernedFieldnames(tgt, allFields, triggerFields);
        if (governed.includes(field.fieldname)) {
          isTargeted = true;
          break;
        }
      }
    }

    if (isTargeted) {
      targetingRules.push(logic);
    }
  });

  return targetingRules;
}

/**
 * Determine if a field should be visible based on:
 * 1. The field's `hidden` property (base state)
 * 2. Conditional logic rules targeting this field
 *
 * Rule precedence & behavior:
 * - If a field is targeted by any "Hide Field" rules and any condition is met: field is hidden (false).
 * - If a field is targeted by any "Show Field" rules: field is ONLY visible if at least
 *   one of those "Show Field" conditions is met. If none are met, the field is hidden (false).
 * - If only "Hide Field" rules exist and none are met: field retains its base visibility (!field.hidden).
 * - If no rules target this field: field retains its base visibility (!field.hidden).
 */
export function shouldFieldBeVisible(
  field: FormField,
  formValues: Record<string, any>,
  allFields: FormField[]
): boolean {
  const baseIsVisible = !field.hidden;

  const targetingRules = findTargetingRules(field, allFields);

  // If no rules target this field, use the base hidden state
  if (targetingRules.length === 0) {
    return baseIsVisible;
  }

  const showRules = targetingRules.filter((r) => r.action === Actions.ShowField);
  const hideRules = targetingRules.filter((r) => r.action === Actions.HideField);

  // 1. Any Hide Field rule satisfied -> hide the field
  for (const rule of hideRules) {
    if (evaluateConditions(rule, formValues, allFields)) {
      return false;
    }
  }

  // 2. If Show Field rules target this field, it is ONLY visible if at least one Show rule passes
  if (showRules.length > 0) {
    return showRules.some((rule) => evaluateConditions(rule, formValues, allFields));
  }

  // 3. If only Hide rules existed and none were met, fallback to base visibility
  return baseIsVisible;
}

/**
 * Determine if a field should be required based on conditional logic
 */
export function shouldFieldBeRequired(
  field: FormField,
  formValues: Record<string, any>,
  allFields: FormField[]
): boolean {
  // If the field is not currently visible, it cannot be required
  if (!shouldFieldBeVisible(field, formValues, allFields)) {
    return false;
  }

  // Start with the field's base required status
  let isRequired = Boolean(field.reqd) && !(field as any).read_only;

  // Find all conditional logic rules that target this field with "Require Answer"
  const targetingRules = findTargetingRules(field, allFields);
  const requireRules = targetingRules.filter((r) => r.action === Actions.RequireAnswer);

  for (const rule of requireRules) {
    if (evaluateConditions(rule, formValues, allFields)) {
      isRequired = true;
      break;
    }
  }

  return isRequired;
}

/**
 * Get all fields that should be visible based on current form values
 */
export function getVisibleFields(
  fields: FormField[],
  formValues: Record<string, any>
): FormField[] {
  return fields.filter((field) =>
    shouldFieldBeVisible(field, formValues, fields)
  );
}
