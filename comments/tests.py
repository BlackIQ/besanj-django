from django.test import TestCase, Client
from .models import *
from account.models import Profile


class TestCommentCreation(TestCase):
    def setUp(self):
        self.client = Client()

        self.user1 = User(username="a", password='123')
        self.user1.save()
        self.user1.profile = Profile(api_token='1')
        self.user1.profile.save()

        self.user2 = User(username="b", password='123')
        self.user2.save()
        self.user2.profile = Profile(api_token='2')
        self.user2.profile.save()

        self.poll1 = Poll.objects.create(title='a', user=self.user1, description='a', is_published=True)
        self.poll2 = Poll.objects.create(title='b', user=self.user1, description='b', is_published=True)
        self.poll3 = Poll.objects.create(title='c', user=self.user1, description='c', is_published=False)

        self.comment1 = Comment.objects.create(user=self.user2, poll=self.poll1, text="test", is_published=True)
        self.comment2 = Comment.objects.create(user=self.user2, poll=self.poll1, text="hi", is_published=False)

    def test_user_cannot_send_comment_without_authentication(self):
        res = self.client.post('/comments/send/')
        self.assertEquals(res.status_code, 401)

        res = self.client.post('/comments/send/', HTTP_TOKEN='2')
        self.assertEquals(res.status_code, 400)

        res = self.client.post('/comments/send/', {'poll_id': 123}, HTTP_TOKEN='2')
        self.assertEquals(res.status_code, 400)

        res = self.client.post('/comments/send/', {'text': 'test'}, HTTP_TOKEN='2')
        self.assertEquals(res.status_code, 400)

    def test_comment_cannot_be_sent_on_wrong_poll(self):
        res = self.client.post('/comments/send/', {'text': 'test', 'poll_id': 12345}, HTTP_TOKEN='2')
        self.assertEquals(res.status_code, 404)

        res = self.client.post('/comments/send/', {'text': 'test', 'poll_id': self.poll3.id}, HTTP_TOKEN='2')
        self.assertEquals(res.status_code, 404)

    def test_comment_cannot_be_sent_on_wrong_parent_comment(self):
        res = self.client.post('/comments/send/', {
            'text': 'test',
            'poll_id': self.poll2.id,
            'parent_comment_id': 12345
        }, HTTP_TOKEN='2')
        self.assertEquals(res.status_code, 404)

        res = self.client.post('/comments/send/', {
            'text': 'test',
            'poll_id': self.poll2.id,
            'parent_comment_id': self.comment2.id
        }, HTTP_TOKEN='2')
        self.assertEquals(res.status_code, 404)

    def test_comment_can_be_sent(self):
        res = self.client.post('/comments/send/', {
            'text': 'created',
            'poll_id': self.poll2.id,
            'parent_comment_id': self.comment1.id
        }, HTTP_TOKEN='2')
        self.assertEquals(res.status_code, 201)
        res_json = res.json()['created_comment']

        created_comment = Comment.objects.filter(text='created', poll=self.poll2, parent_comment=self.comment1).get()
        self.assertEquals(created_comment.user.id, self.user2.id)

        self.assertEquals(res_json['id'], created_comment.id)
        self.assertEquals(res_json['poll_id'], created_comment.poll.id)
        self.assertEquals(res_json['parent_comment_id'], created_comment.parent_comment.id)
        self.assertEquals(res_json['user']['email'], created_comment.user.email)
        self.assertEquals(res_json['is_published'], created_comment.is_published)

        res = self.client.post('/comments/send/', {
            'text': 'sent',
            'poll_id': self.poll1.id,
        }, HTTP_TOKEN='1')
        self.assertEquals(res.status_code, 201)
        res_json = res.json()['created_comment']

        created_comment = Comment.objects.filter(text='sent', poll=self.poll1, parent_comment=None).get()
        self.assertEquals(created_comment.user.id, self.user1.id)

        self.assertEquals(res_json['id'], created_comment.id)
        self.assertEquals(res_json['poll_id'], created_comment.poll.id)
        self.assertEquals(res_json['user']['email'], created_comment.user.email)
        self.assertEquals(res_json['is_published'], created_comment.is_published)
        self.assertTrue('parent_comment_id' not in res_json)


class TestCommentDeletion(TestCase):
    def setUp(self):
        self.client = Client()

        self.user1 = User(username="a", password='123')
        self.user1.save()
        self.user1.profile = Profile(api_token='1')
        self.user1.profile.save()

        self.user2 = User(username="b", password='123')
        self.user2.save()
        self.user2.profile = Profile(api_token='2')
        self.user2.profile.save()

        self.poll1 = Poll.objects.create(title='a', user=self.user1, description='a', is_published=True)

        self.comment1 = Comment.objects.create(user=self.user1, poll=self.poll1, text="test", is_published=True)
        self.comment2 = Comment.objects.create(user=self.user2, poll=self.poll1, text="hi", is_published=True)

    def test_user_cannot_delete_comment_without_authentication(self):
        res = self.client.post('/comments/delete/')
        self.assertEquals(res.status_code, 401)

        res = self.client.post('/comments/delete/', HTTP_TOKEN='1')
        self.assertEquals(res.status_code, 404)

        res = self.client.post('/comments/delete/', {'comment_id': 12345}, HTTP_TOKEN='1')
        self.assertEquals(res.status_code, 404)

    def test_user_cannot_delete_comment_of_other_user(self):
        res = self.client.post('/comments/delete/', {'comment_id': self.comment2.id}, HTTP_TOKEN='1')
        self.assertEquals(res.status_code, 403)

    def test_user_can_delete_comment(self):
        res = self.client.post('/comments/delete/', {'comment_id': self.comment1.id}, HTTP_TOKEN='1')
        self.assertEquals(res.status_code, 200)
        self.assertFalse(Comment.objects.filter(pk=self.comment1.id).exists())

