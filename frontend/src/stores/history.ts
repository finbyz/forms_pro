import { defineStore } from "pinia";
import { ref } from "vue";

export const useHistoryStore = defineStore("history", () => {
    const past = ref<any[]>([]);
    const future = ref<any[]>([]);

    const saveState = (state: any) => {
        past.value.push(JSON.parse(JSON.stringify(state)));
        future.value = []; // Clear future on new action
    };

    const undo = (currentState: any) => {
        if (past.value.length === 0) return currentState;
        const previous = past.value.pop();
        future.value.push(JSON.parse(JSON.stringify(currentState)));
        return previous;
    };

    const redo = (currentState: any) => {
        if (future.value.length === 0) return currentState;
        const next = future.value.pop();
        past.value.push(JSON.parse(JSON.stringify(currentState)));
        return next;
    };

    return { past, future, saveState, undo, redo };
});
