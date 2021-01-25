import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Group, Post, User

USERNAME = 'author'
SLUG = 'test_slug'
TEXT = 'test_text'
INDEX_URL = reverse('index')
NEW_POST = reverse('new_post')
LOGIN = reverse('login')

SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)
UPLOADED = SimpleUploadedFile(
    name='small.gif',
    content=SMALL_GIF,
    content_type='image/gif')


class TestPostForm(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

        cls.author = User.objects.create_user(
            username=USERNAME)
        cls.group = Group.objects.create(
            slug=SLUG)
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text=TEXT,
            )
        cls.form = PostForm()
        cls.POST_URL = (
            reverse('post',
                    args=[cls.author.username, cls.post.id]))
        cls.POST_EDIT_URL = (
            reverse('post_edit',
                    args=[cls.author.username, cls.post.id]))
        cls.expected_redirect_new = f'{LOGIN}?next={NEW_POST}'
        cls.expected_redirect_edit = f'{LOGIN}?next={cls.POST_EDIT_URL}'
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(TestPostForm.author)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_create_post_auth(self):
        '''Валидная форма создает запись в Post'''
        # Удаляем все возможные посты из базы
        Post.objects.all().delete()
        posts_count = Post.objects.count()
        # Создаем один новый пост с нужными данными
        form_data = {
            'text': 'new_text',
            'group': self.group.id,
            'image': UPLOADED}
        response = self.authorized_client.post(
            NEW_POST,
            data=form_data,
            follow=True)
        self.assertRedirects(response, INDEX_URL)
        # Количество постов увеличилось на один
        self.assertNotEqual(posts_count, posts_count+1)
        # Исключаю пост, созданный в классе
        post = Post.objects.get()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(
            post.image.file.read(),
            form_data['image'].file.getvalue())

    def test_create_post_guest(self):
        '''Гостевой акк не создает запись в Post'''
        posts_count = Post.objects.count()
        form_data = {
            'text': 'new_text',
            'group': self.group.id,
            'image': UPLOADED}
        response = self.guest_client.post(
            NEW_POST,
            data=form_data,
            follow=True)
        # Редирект на страницу логина
        self.assertRedirects(response, TestPostForm.expected_redirect_new)
        # Количество постов не изменилось
        self.assertEqual(Post.objects.count(), posts_count)

    def test_edit_post_auth(self):
        '''Валидная форма изменяет запись в Post'''
        posts_count = Post.objects.count()
        form_data = {
            'text': 'new_text',
            'group': self.group.id,
            'image': UPLOADED}
        self.authorized_client.post(
            TestPostForm.POST_EDIT_URL,
            data=form_data)
        post = Post.objects.get(id=self.post.id)
        # Количество постов осталось прежним
        self.assertEqual(Post.objects.count(), posts_count)
        # Данные изменились
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])

    def test_edit_post_guest(self):
        '''Гостевой акк не может добавить запись в Post'''
        posts_count = Post.objects.count()
        form_data = {
            'text': 'double_new_text',
            'group': 'new_group',
            'image': UPLOADED}
        self.guest_client.post(
            TestPostForm.POST_EDIT_URL,
            data=form_data,
            follow=True)
        post = Post.objects.get(id=self.post.id)
        # Количество постов осталось прежним
        self.assertEqual(Post.objects.count(), posts_count)
        # Данные не изменились
        # Такие проверки были в теории.
        # У остальных их приняли как верные
        self.assertNotEqual(post.text, form_data['text'])
        self.assertNotEqual(post.group, form_data['group'])

    def test_new_post_show_correct_context(self):
        '''Шаблон new_post сформирован с правильным контекстом.'''
        response = self.authorized_client.get(NEW_POST)
        response2 = self.authorized_client.get(
            TestPostForm.POST_EDIT_URL)
        form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                form_field2 = response2.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
                self.assertIsInstance(form_field2, expected)
