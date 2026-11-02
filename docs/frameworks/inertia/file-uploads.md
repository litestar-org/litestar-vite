# File Uploads

Inertia's `useForm` and `router` automatically detect `File` or `Blob` objects anywhere inside your form data (including nested objects and arrays), convert the request payload into `multipart/form-data`, and emit real-time upload progress events.

---

## 1. Handling `UploadFile` in Litestar

Use Litestar's `RequestEncodingType.MULTI_PART` and `UploadFile` (or `list[UploadFile]`) inside a `msgspec.Struct` or dataclass to accept single or multiple file uploads alongside regular form fields:

```python title="app.py"
from pathlib import Path
from typing import Annotated, Any

from litestar import Request, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from msgspec import Struct
from litestar_vite.inertia import InertiaRedirect, flash


class UpdateAvatarPayload(Struct):
    display_name: str
    avatar: UploadFile


class UploadDocumentsPayload(Struct):
    folder: str
    documents: list[UploadFile]


@post("/profile/avatar", name="profile.avatar", sync_to_thread=False)
async def update_avatar(
    request: Request[Any, Any, Any],
    data: Annotated[UpdateAvatarPayload, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> InertiaRedirect:
    """Read uploaded avatar bytes and redirect back to profile."""
    content = await data.avatar.read()
    target = Path("uploads") / (data.avatar.filename or "avatar.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    flash(request, f"Uploaded avatar for {data.display_name} ({len(content)} bytes)", category="success")
    return InertiaRedirect(request, redirect_to="/profile")
```

---

## 2. Frontend File Inputs, Previews & Progress Bars

`form.progress` provides `{ percentage, loaded, total }` while a multipart upload is in flight:

=== "React (`@inertiajs/react`)"

    ```tsx title="resources/pages/Profile/AvatarForm.tsx"
    import { type ChangeEvent, type FormEvent, useState } from "react";
    import { useForm } from "@inertiajs/react";
    import { route } from "@/generated/routes";

    export function AvatarForm({ currentName }: { currentName: string }) {
      const [previewUrl, setPreviewUrl] = useState<string | null>(null);
      const form = useForm<{ display_name: string; avatar: File | null }>({
        display_name: currentName,
        avatar: null,
      });

      function onFileChange(e: ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0] ?? null;
        form.setData("avatar", file);
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setPreviewUrl(file ? URL.createObjectURL(file) : null);
      }

      function onSubmit(e: FormEvent) {
        e.preventDefault();
        form.post(route("profile.avatar"), {
          forceFormData: true,
        });
      }

      return (
        <form onSubmit={onSubmit}>
          <input
            value={form.data.display_name}
            onChange={(e) => form.setData("display_name", e.target.value)}
          />
          <input type="file" accept="image/*" onChange={onFileChange} />

          {previewUrl && <img src={previewUrl} alt="Avatar preview" width={96} height={96} />}

          {form.progress && (
            <progress value={form.progress.percentage} max={100}>
              {form.progress.percentage}%
            </progress>
          )}

          <button type="submit" disabled={form.processing}>
            Save Avatar
          </button>
        </form>
      );
    }
    ```

=== "Vue 3 (`@inertiajs/vue3`)"

    ```vue title="resources/pages/Profile/AvatarForm.vue"
    <script setup lang="ts">
    import { ref } from "vue";
    import { useForm } from "@inertiajs/vue3";
    import { route } from "@/generated/routes";

    const props = defineProps<{ currentName: string }>();
    const previewUrl = ref<string | null>(null);

    const form = useForm<{ display_name: string; avatar: File | null }>({
      display_name: props.currentName,
      avatar: null,
    });

    function onFileChange(event: Event) {
      const input = event.target as HTMLInputElement;
      const file = input.files?.[0] ?? null;
      form.avatar = file;
      if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
      previewUrl.value = file ? URL.createObjectURL(file) : null;
    }

    function submit() {
      form.post(route("profile.avatar"), { forceFormData: true });
    }
    </script>

    <template>
      <form @submit.prevent="submit">
        <input v-model="form.display_name" />
        <input type="file" accept="image/*" @change="onFileChange" />

        <img v-if="previewUrl" :src="previewUrl" alt="Avatar preview" width="96" height="96" />

        <progress v-if="form.progress" :value="form.progress.percentage" max="100">
          {{ form.progress.percentage }}%
        </progress>

        <button type="submit" :disabled="form.processing">Save Avatar</button>
      </form>
    </template>
    ```

---

## 3. Multipart Updates with `PUT` / `PATCH`

When updating a resource that includes a file upload, prefer `POST` (or pass `_method: "put"` if using method spoofing) with `forceFormData: true` so the browser encodes the payload as `multipart/form-data`.
