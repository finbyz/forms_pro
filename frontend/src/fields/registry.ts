export interface FieldDefinition {
    type: string;
    category: "BASIC" | "CHOICE" | "DATE_TIME" | "RELATION" | "UPLOAD" | "LAYOUT" | "ADVANCED";
    storesValue: boolean;
    supportsOptions: boolean;
    supportsDefault: boolean;
    supportsRequired: boolean;
    supportedTargetTypes: string[];
}

export const FieldRegistry: Record<string, FieldDefinition> = {
    "Data": {
        type: "Data",
        category: "BASIC",
        storesValue: true,
        supportsOptions: false,
        supportsDefault: true,
        supportsRequired: true,
        supportedTargetTypes: ["Data", "Small Text"]
    },
    "Text": {
        type: "Text",
        category: "BASIC",
        storesValue: true,
        supportsOptions: false,
        supportsDefault: true,
        supportsRequired: true,
        supportedTargetTypes: ["Text", "Long Text", "Text Editor"]
    },
    "Select": {
        type: "Select",
        category: "CHOICE",
        storesValue: true,
        supportsOptions: true,
        supportsDefault: true,
        supportsRequired: true,
        supportedTargetTypes: ["Select"]
    },
    "Heading": {
        type: "Heading",
        category: "LAYOUT",
        storesValue: false,
        supportsOptions: false,
        supportsDefault: false,
        supportsRequired: false,
        supportedTargetTypes: []
    }
    // Other fields would go here...
};
