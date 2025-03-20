from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import User, FriendRequest
from schemas import FriendRequestCreate, FriendRequestAccept, FriendRequestRemove