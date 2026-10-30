import { css } from "lit";

export default css`
  /* The message band spans the full card width at a fixed offset, and it is
     drawn after the other elements, so it sits on top of them. Left
     interactive it would swallow clicks aimed at whatever it overlaps —
     including when it has no message to show and is visually empty.
     Pointer events are re-enabled on the content below, so the message text
     and its trash button stay clickable when there is something to see. */
  :host {
    pointer-events: none;
  }

  .messages_content {
    pointer-events: auto;
  }

  /* A click on the text opens the message history */
  .messages_text {
    cursor: pointer;
  }
`;
