import { z, defineCollection } from "astro:content";
const projectSchema = z.object({
  title: z.string(),
  description: z.string(),
  pubDate: z.coerce.date(),
  updatedDate: z.coerce.date(),
  heroImage: z.string().optional(),
  badge: z.string().optional(),
  tags: z
    .array(z.string())
    .refine((items) => new Set(items).size === items.length, {
      message: "tags must be unique",
    })
    .optional(),
});

const storeSchema = z.object({
  title: z.string(),
  description: z.string(),
  custom_link_label: z.string(),
  custom_link: z.string().optional(),
  updatedDate: z.coerce.date(),
  pricing: z.string().optional(),
  oldPricing: z.string().optional(),
  badge: z.string().optional(),
  checkoutUrl: z.string().optional(),
  heroImage: z.string().optional(),
});

export type ProjectSchema = z.infer<typeof projectSchema>;
export type StoreSchema = z.infer<typeof storeSchema>;

const projectCollection = defineCollection({ schema: projectSchema });
const storeCollection = defineCollection({ schema: storeSchema });

export const collections = {
  projects: projectCollection,
  store: storeCollection,
};
