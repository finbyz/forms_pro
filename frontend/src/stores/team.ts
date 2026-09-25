import { defineStore } from "pinia";
import { useUser } from "./user";
import { computed, ref, watch } from "vue";
import { createResource } from "frappe-ui";
import { toast } from "vue-sonner";

export type TeamMember = {
  full_name: string;
  user_image: string | null;
  email: string;
  can_edit_team: boolean;
  is_owner: boolean;
};

export const useTeam = defineStore("team", () => {
  const user = useUser();
  const currentTeam = computed(() => user.currentTeam);
  const activeTeamId = ref<string | null>(null);

  const targetTeamId = computed(() => activeTeamId.value || currentTeam.value?.name || null);

  const teamMembersResource = createResource({
    url: "forms_pro.api.team.get_team_members",
    makeParams() {
      return {
        team_id: targetTeamId.value,
      };
    },
  });

  const teamMembers = computed<TeamMember[]>(() => {
    const data = teamMembersResource.data;
    return Array.isArray(data) ? data : [];
  });

  function initialize(teamId?: string) {
    if (teamId) {
      activeTeamId.value = teamId;
    }
    if (targetTeamId.value) {
      teamMembersResource.fetch({ team_id: targetTeamId.value });
    }
  }

  function addMemberToTeam(user_email: string, team_id?: string): Promise<void> {
    const effectiveTeamId = team_id || targetTeamId.value;
    return new Promise((resolve, reject) => {
      createResource({
        url: "forms_pro.api.team.add_team_member",
        method: "POST",
        makeParams() {
          return {
            team_id: effectiveTeamId,
            user_email,
          };
        },
        async onSuccess() {
          if (effectiveTeamId) {
            await teamMembersResource.fetch({ team_id: effectiveTeamId });
          }
          toast.success("Team member added successfully");
          resolve();
        },
        onError(error: Error) {
          console.error(error);
          toast.error(`Failed to add team member: ${error.message}`);
          reject(error);
        },
      }).submit();
    });
  }

  function toggleEditPermissionForMember(member_email: string) {
    createResource({
      url: "forms_pro.api.team.toggle_can_edit_team",
      method: "POST",
      makeParams() {
        return {
          team_id: targetTeamId.value,
          member_email: member_email,
        };
      },
      async onSuccess() {
        await teamMembersResource.fetch({ team_id: targetTeamId.value });
        toast.info("Edit Permission Updated");
      },
      onError(error: Error) {
        console.error(error);
        toast.error(`Failed to update edit permission`);
      },
    }).submit();
  }

  function removeMemberFromTeam(member_email: string) {
    createResource({
      url: "forms_pro.api.team.remove_member_from_team",
      method: "POST",
      makeParams() {
        return {
          team_id: targetTeamId.value,
          member_email: member_email,
        };
      },
      async onSuccess() {
        await teamMembersResource.fetch({ team_id: targetTeamId.value });
        toast.success("Member removed from team");
      },
      onError(error: Error) {
        console.error(error);
        toast.error(`Failed to remove member from team`);
      },
    }).submit();
  }

  async function save(fields: { team_name?: string; logo?: string }) {
    createResource({
      url: "forms_pro.api.team.save",
      method: "POST",
      makeParams() {
        return {
          team_id: targetTeamId.value,
          fields,
        };
      },
      async onSuccess() {
        toast.success("Team Details Updated");
        await teamMembersResource.fetch({ team_id: targetTeamId.value });
        user.fetchUserTeams();
      },
      onError(error: Error) {
        console.error(error);
        toast.error("Failed to update team " + error.message);
      },
    }).submit();
  }

  watch(
    () => currentTeam.value?.name,
    (newTeamId) => {
      if (newTeamId && !activeTeamId.value) {
        teamMembersResource.fetch({ team_id: newTeamId });
      }
    },
    { immediate: true }
  );

  return {
    currentTeam,
    activeTeamId,
    targetTeamId,
    teamMembers,
    teamMembersResource,
    initialize,
    addMemberToTeam,
    toggleEditPermissionForMember,
    removeMemberFromTeam,
    save,
  };
});

