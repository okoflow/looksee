<!--
Write this body the way this repository writes commit messages: complete sentences,
present tense, mechanism before consequence, no headings and no checklists. One to
three sentences is the usual size, and a dependency bump needs one. If the description
keeps growing, the pull request is probably too large to review in one sitting, and
splitting it is the better fix.

Use bullets only when the change crosses more than one area (api, inference, studio,
docs, compose), and group them by that area.

Describe what this branch already does. Planned work belongs in an issue that this
pull request links, never as unticked boxes here.

The shape:

  One to three sentences: what the change does, and why it is needed.

  Breaking: what an operator has to do — recreate a volume, set a new environment
  variable, migrate a changed workflow schema. Keep this line only when it is true.

  Verified: what you ran and what you saw beyond the checks CI already runs (lint,
  formatting, the migration check, typecheck, build, and the service images). Runtime
  smoke tests, manual exercise, stand-ins for external services. On a documentation or
  typo change write "nothing beyond CI" rather than dropping the line.

  Fixes #N, or Part of #N when the issue stays open afterwards. Delete the line when
  there is no issue.

The title becomes the merge commit subject, so write it as the commit subject it will
be: "feat: owner auth and encrypted credential store", not "feat: worktrees updates".
-->

Verified: 
