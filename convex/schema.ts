import { defineSchema, defineTable } from 'convex/server';
import { v } from 'convex/values';

export default defineSchema({
  groups: defineTable({
    name: v.string(),
    description: v.string(),
    icon_url: v.string(), // Can be Convex file ID or local asset reference
  }),

  messages: defineTable({
    group_id: v.id('groups'),
    user: v.string(),             // user ID or name
    content: v.string(),          // text message (can be empty if only audio)
    file: v.optional(v.string()), // optional image or document URL / file ID
    audio: v.optional(v.string()),// ✅ NEW: audio file URL or Convex file ID
    created_at: v.number(),       // optional timestamp if needed
  }),
});
