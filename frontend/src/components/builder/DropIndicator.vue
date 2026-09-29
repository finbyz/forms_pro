<script setup lang="ts">
/**
 * The line showing where a dragged field would land.
 *
 * This is the whole of the drag's visual feedback. Nothing on the canvas
 * moves while dragging -- no card is lifted out of the layout, nothing
 * reflows, no placeholder is inserted -- so there is nothing to stutter. The
 * form is only rearranged once, on drop.
 *
 * Fixed positioning in viewport coordinates, which is what the geometry
 * already works in, and `pointer-events: none` so the line can never become
 * its own drop target.
 */
import { computed } from "vue";
import type { Indicator } from "@/utils/dropGeometry";

const props = defineProps<{ indicator: Indicator | null }>();

const THICKNESS = 3;

const style = computed(() => {
    const line = props.indicator;
    if (!line) return undefined;

    if (line.orientation === "vertical") {
        return {
            left: `${line.left - THICKNESS / 2}px`,
            top: `${line.top}px`,
            width: `${THICKNESS}px`,
            height: `${line.length}px`,
        };
    }
    return {
        left: `${line.left}px`,
        top: `${line.top - THICKNESS / 2}px`,
        width: `${line.length}px`,
        height: `${THICKNESS}px`,
    };
});

const isVertical = computed(() => props.indicator?.orientation === "vertical");
</script>

<template>
    <Teleport to="body">
        <div
            v-if="indicator"
            class="fixed z-[250] rounded-full bg-surface-blue-6 pointer-events-none"
            :style="style"
            aria-hidden="true"
        >
            <!-- End caps, so a short line still reads as an insertion point. -->
            <span
                class="absolute h-[7px] w-[7px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-inherit"
                :class="isVertical ? 'left-1/2 top-0' : 'left-0 top-1/2'"
            />
            <span
                class="absolute h-[7px] w-[7px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-inherit"
                :class="isVertical ? 'left-1/2 top-full' : 'left-full top-1/2'"
            />
        </div>
    </Teleport>
</template>
