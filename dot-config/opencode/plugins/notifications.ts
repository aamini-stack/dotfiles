export const NotificationPlugin = async ({
  project,
  client,
  $,
  directory,
  worktree,
}) => {
  return {
    event: async ({ event }) => {
      // Send notification on session completion
      if (event.type === "permission.asked") {
        await $`osascript -e 'display notification "Permission required!" with title "opencode"'`;
      }
    },
  };
};
