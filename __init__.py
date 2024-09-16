from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, getText
from anki.hooks import addHook
from anki.notes import Note
import re

def auto_link_keyword(editor):
    # Get the current note
    note = editor.note
    if not note:
        showInfo("No note selected.")
        return

    # Get the keyword from the user
    keyword, ok = getText("Enter the keyword to auto-link:")
    if not ok or not keyword:
        return

    # Get the current deck
    deck_id = editor.card.did
    deck = mw.col.decks.get(deck_id)
    deck_name = deck['name']

    # Search for notes in the current deck containing the keyword
    query = f'"deck:{deck_name}" {keyword}'
    note_ids = mw.col.findNotes(query)

    # Replace the keyword with the link in all matching notes
    linked_notes = 0
    for nid in note_ids:
        if nid == note.id:
            continue  # Skip the current note
        current_note = mw.col.getNote(nid)
        for field_name, field_value in current_note.items():
            # Use regex to find keywords not already in link format
            new_value = re.sub(
                f'(?<!\\[){re.escape(keyword)}(?!\\|nid\\d+\\])',
                f'[{keyword}|nid{note.id}]',
                field_value,
		flags=re.IGNORECASE
            )
            if new_value != field_value:
                current_note[field_name] = new_value
                linked_notes += 1
        current_note.flush()

    # Add the AutoLinked tag
    current_tags = note.tags
    new_tag = f"AutoLinked::{keyword}"
    if new_tag not in current_tags:
        current_tags.append(new_tag)
    note.tags = current_tags


    # Update the editor
    editor.loadNote()
    editor.web.eval("focusField(%d);" % editor.currentField)

    showInfo(f"Auto-linked '{keyword}' in {linked_notes} notes.")


def undo_auto_link(editor):
    # Get the current note (definition note)
    note = editor.note
    if not note:
        showInfo("No note selected.")
        return

    # Find AutoLinkedDefinition tags
    auto_linked_def_tags = [tag for tag in note.tags if tag.startswith("AutoLinked::")]
    
    if not auto_linked_def_tags:
        showInfo("No auto-linked definitions found in this note.")
        return

    unlinked_count = 0
    for tag in auto_linked_def_tags:
        keyword = tag.split("::")[-1]
        
        # Search for notes in all decks containing the link
        query = f're:\\[{re.escape(keyword)}\\|nid{note.id}\\]'
        note_ids = mw.col.findNotes(query)

        for nid in note_ids:
            current_note = mw.col.getNote(nid)
            for field_name, field_value in current_note.items():
                # Remove links for this keyword
                new_value = re.sub(
                    f'\\[{re.escape(keyword)}\\|nid{note.id}\\]',
                    keyword,
                    field_value
                )
                if new_value != field_value:
                    current_note[field_name] = new_value
                    unlinked_count += 1
            current_note.flush()

        # Remove the AutoLinkedDefinition tag from the definition note
        note.tags.remove(tag)

    note.flush()

    # Update the editor
    editor.loadNote()
    editor.web.eval("focusField(%d);" % editor.currentField)

    showInfo(f"Unlinked {unlinked_count} instances across all notes.")

def add_auto_link_button(buttons, editor):
    return buttons + [
        editor.addButton(
            icon=None,
            cmd='auto_link_keyword',
            func=lambda e=editor: auto_link_keyword(e),
            tip="Auto Link Keyword",
            keys=None
        ),
        editor.addButton(
            icon=None,
            cmd='undo_auto_link',
            func=lambda e=editor: undo_auto_link(e),
            tip="Undo Auto Link",
            keys=None
        )
    ]

addHook("setupEditorButtons", add_auto_link_button)
