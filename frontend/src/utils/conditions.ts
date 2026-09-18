export const evaluateCondition = (condition: any, formData: Record<string, any>) => {
    const value = formData[condition.field_key];
    const targetValue = condition.value;

    switch (condition.operator) {
        case "equals":
            return String(value) === String(targetValue);
        case "not_equals":
            return String(value) !== String(targetValue);
        case "contains":
            return String(value).includes(String(targetValue));
        case "is_empty":
            return !value;
        case "is_not_empty":
            return !!value;
        default:
            return false;
    }
};

export const evaluateLogic = (logic: any, formData: Record<string, any>) => {
    if (!logic || !logic.conditions || logic.conditions.length === 0) return true;

    if (logic.match === "All") {
        return logic.conditions.every((cond: any) => evaluateCondition(cond, formData));
    } else {
        return logic.conditions.some((cond: any) => evaluateCondition(cond, formData));
    }
};
