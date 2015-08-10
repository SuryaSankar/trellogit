# trellogit

A very very opinionated way of syncing Github Issues and Trello. Use it if it suits you.

Design Goal
============

1. Calendar view for Github milestones via Trello's Calendar Powerup.

2. Assign priority for tasks by positioning them in the Kanban list. This is more
powerful than P1, P2 which just serves to classify the issue.

3. Allow non-dev tasks and dev tasks to exist on the same board when they are interdependent

4. Split milestones into tasks. Assign and track separately.

5. Seamless Two way binding between issues in Github and Tasks in Trello

6. Allow a task to be marked as "Burning" which would mean that everything else has to be dropped
and this has to be addressed first.

7. Have both "Polling" and "Web Hook" ways of doing this. Not everyone needs to set up a server to listen to hooks. Polling might work just fine for some.


Idea
=====

1. Create a "Milestones" board to track your milestones. Each milestone is a card with a due date.
It will be synced with your github milestones. Creating a milestone card in Trello will create a github milestone and vice versa. Milestones move from To Do -> Doing -> Done.

2. Create a "Tasks" board to track the individual tasks. All Github Issues will get added to this board. Those which have milestone marked on them will have the milestone marked as a label, so that
we can filter by those labels to see the status of tasks

3. Issues which get comments or which are referenced in commits should move to the "Doing" queue automatically and those which get "fixed" should move to Done queue automatically. Similarly moving
the card between lists will also change the status of linked issue in github.

4. If any Task/Issue of a milestone moves to the Doing Queue, the milestone will also move to the
"Doing" list. If all tasks/issues of a milestone move to the "Done" list, the milestone will also
move to the Done list

5. Enable a summary view of the tasks in the Milestones board itself by mapping each Task card to a checklist item and grouping the checklists by the assignee name. The checklist should get automatically checked when the corresponding task gets moved to "Done" list